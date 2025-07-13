# realtime_runner.py
#
# Changelog:
# - Integrated console_status utilities for consistent output
# - Added drawdown limit check via RiskManager
# - Dynamic stop reason on loop exit
# - Fixed max loss check to ignore non-positive limits

import os
import time
import traceback
from datetime import datetime

from data_provider import fetch_latest_candle, fetch_last_price, get_last_candle_time
from cooldown_manager import CooldownManager
from session_filter import SessionFilter
from status_block import print_entry_status
from gui_bridge import GUIBridge
from gui import TradingGUI, TradingGUILogicMixin
from config import SETTINGS
from global_state import (
    entry_time_global,
    ema_trend_global,
    atr_value_global,
    position_global,
)
import global_state

from indicator_utils import calculate_ema, calculate_atr

# NEU: Adaptive Engines
from andac_entry_master import AndacEntryMaster, AndacSignal
from adaptive_sl_manager import AdaptiveSLManager

from risk_manager import RiskManager
from console_status import (
    print_start_banner,
    print_stop_banner,
    print_warning,
    print_info,
)
from pnl_utils import calculate_futures_pnl, check_plausibility

FEE_RATE = 0.0004  # Trading fee per side

API_KEY = SETTINGS.get("api_key", "")
API_SECRET = SETTINGS.get("api_secret", "")

gui_bridge = None

def live_partial_close(trader, symbol, side, qty):
    reduce_side = "SELL" if side == "long" else "BUY"
    try:
        trader.place_order(
            symbol,
            reduce_side,
            qty,
            reduce_only=True,
            order_type="MARKET"
        )
        print(f"⚡️ LIVE-Teilschließung: {qty} {reduce_side} via Reduce Only Market")
    except Exception as e:
        print(f"❌ Fehler beim Live-Teilverkauf: {e}")

def set_gui_bridge(gui_instance):
    global gui_bridge
    gui_bridge = GUIBridge(gui_instance)

def cancel_trade(position, app):
    """Schließt die Position und setzt sie auf None"""
    print(f"❌ Abbruch der Position: {position['side']} @ {position['entry']:.2f}")
    # Position schließen
    app.position = None  # Position auch in der App auf None setzen
    app.log_event("🛑 Position wurde durch Benutzer abgebrochen!")  # Log-Ereignis
    return None  # Rückgabe von None, um die Position zu schließen

def emergency_exit_position(app):
    """Löst den Notausstieg aus und schließt alle Positionen"""
    if app.position:
        print("❗️ Notausstieg ausgelöst! Die Position wird geschlossen.")
        cancel_trade(app.position, app)  # Aufruf der cancel_trade Funktion
        app.log_event("🛑 Position wurde im Notausstiegsmodus geschlossen!")
    else:
        print("❌ Keine Position offen, um sie zu schließen!")
        app.log_event("❌ Keine offene Position zum Notausstiegsmodus gefunden.")  # Nachricht wenn keine Position da ist

def run_bot_live(settings=None, app=None):
    global entry_time_global, position_global, ema_trend_global, atr_value_global
    print_info("Debug: Überprüfe die Signalverarbeitung...")

    capital = SETTINGS.get("starting_capital", 1000)
    start_capital = capital

    print_start_banner(capital)

    if app:
        settings["log_event"] = app.log_event
        set_gui_bridge(app)
        start_capital = capital

    # --- HIER Manager initialisieren ---
    risk_manager = RiskManager(app, start_capital)

    # --- HIER: GUI/Bridge-Parameter einlesen ---
    multiplier = gui_bridge.multiplier
    capital = float(gui_bridge.capital)      # <--- float!
    start_capital = capital                  # <--- Startwert merken für Verlustlimit
    interval = gui_bridge.interval
    auto_multi = gui_bridge.auto_multiplier

    live_requested = gui_bridge.live_trading and API_KEY and API_SECRET
    paper_mode = settings.get("paper_mode", True)
    live_trading = live_requested and not paper_mode
    settings["paper_mode"] = not live_trading

    leverage = multiplier
    # interval wird aus GUI übernommen, NICHT überschreiben!

    # Restliche Initialisierung...
    cooldown = CooldownManager(settings.get("cooldown", 3))
    session_filter = SessionFilter()

    andac_params = {
        "lookback": int(app.andac_lookback.get()),
        "puffer": float(app.andac_puffer.get()),
        "vol_mult": float(app.andac_vol_mult.get()),
        "opt_rsi_ema": app.andac_opt_rsi_ema.get(),
        "opt_safe_mode": app.andac_opt_safe_mode.get(),
        "opt_engulf": app.andac_opt_engulf.get(),
        "opt_engulf_bruch": app.andac_opt_engulf_bruch.get(),
        "opt_engulf_big": app.andac_opt_engulf_big.get(),
        "opt_confirm_delay": app.andac_opt_confirm_delay.get(),
        "opt_mtf_confirm": app.andac_opt_mtf_confirm.get(),
        "opt_volumen_strong": app.andac_opt_volumen_strong.get(),
        "opt_session_filter": app.andac_opt_session_filter.get(),
    }
    andac_indicator = AndacEntryMaster(**andac_params)
    adaptive_sl = AdaptiveSLManager()

    trader = None

    candles = []
    position = None
    last_printed_price = None
    last_signal = None
    last_signal_time = 0
    entry_repeat_delay = settings.get("entry_repeat_delay", 3)
    sl_mult = settings["stop_loss_atr_multiplier"]
    tp_mult = settings["take_profit_atr_multiplier"]

    last_printed_pnl = None
    last_printed_price = None

    no_signal_printed = False
    first_feed = False
    candle_warning_printed = False

    while capital > 0 and not getattr(app, "force_exit", False):
        if not getattr(app, "running", False):
            time.sleep(1)
            continue
        if not getattr(app, "feed_ok", True):
            time.sleep(1)
            continue
        risk_manager.update_capital(capital)
        # --- Schutzmechanismen ---
        if risk_manager.check_loss_limit() or risk_manager.check_drawdown_limit():
            time.sleep(1)
            continue

        try:
            candle = fetch_latest_candle(settings["symbol"], interval)
            price = fetch_last_price("binance", settings["symbol"])
            stamp = datetime.now().strftime("%H:%M:%S")
            if price is None and hasattr(app, "log_event"):
                app.log_event("Keine Marktdaten – Exchange: BINANCE")
            if not candle:
                last_candle = get_last_candle_time()
                if last_candle is None or time.time() - last_candle > 5:
                    if not candle_warning_printed:
                        print("⚠️ Keine Candle-Daten.")
                        candle_warning_printed = True
                time.sleep(1)
                continue
            else:
                candle_warning_printed = False

            # Update global timestamp for feed watchdog
            global_state.last_feed_time = time.time()

            if not first_feed:
                first_feed = True
                if hasattr(app, "log_event"):
                    app.log_event("✅ Erster Marktdaten-Feed empfangen")

            candles.append(candle)
            if len(candles) > 100:
                candles.pop(0)

            # Berechnung des ATR und Zuordnung zu atr_value_global
            atr_value_global = calculate_atr(candles, 14) if calculate_atr(candles, 14) is not None else 0.0

            # Der Rest des Codes bleibt unverändert
            close_list = [c["close"] for c in candles[-20:] if "close" in c]
            ema = calculate_ema(close_list, 20)
            settings["ema_value"] = ema

            if ema is not None:
                ema_trend_global = "⬆️" if candle["close"] > ema else "⬇️"
            else:
                ema_trend_global = "❓"

            close_price = candle["close"]
            now = time.time()

        except Exception as e:  # Hier wird der Fehler abgefangen
            print("❌ Fehler im Botlauf:", e)
            traceback.print_exc()
            time.sleep(2)
            continue  # Weiter zum nächsten Loop

        # GUI Empfehlungen/Filter (wie gehabt)
        if hasattr(app, "auto_apply_recommendations") and app.auto_apply_recommendations.get():
            try:
                app.apply_recommendations()
            except Exception as e:
                print(f"⚠️ Automatisches Anwenden fehlgeschlagen: {e}")

        andac_signal: AndacSignal = andac_indicator.evaluate(candle)
        entry_type = andac_signal.signal
        stamp = datetime.now().strftime("%H:%M:%S")
        if entry_type:
            log_msg = (
                f"[{stamp}] Signal erkannt: {entry_type.upper()} "
                f"({settings['symbol']} @ {close_price:.2f})"
            )
            print(log_msg)
            if hasattr(app, "log_event"):
                app.log_event(log_msg)
        elif andac_signal.reasons:
            reason_msg = ", ".join(andac_signal.reasons)
            log_msg = f"[{stamp}] Signal verworfen: {reason_msg}"
            print(log_msg)
            if hasattr(app, "log_event"):
                app.log_event(log_msg)

        # --- POSITION HANDLING ---
        if position:
            current = candle["close"]
            entry = position["entry"]
            pnl_live = calculate_futures_pnl(
                entry,
                current,
                position["leverage"],
                position["amount"],
                position["side"],
            )

            # Nur print bei Veränderung!
            if (
                last_printed_pnl is None or last_printed_price is None or
                abs(pnl_live - last_printed_pnl) > 1.0 or
                abs(current - last_printed_price) > 1.0
            ):
                print(f"⏳ Position offen ({position['side']}) | Entry: {entry:.2f} | Now: {current:.2f}")
                print(f"💰 Aktuelles Balance: ${capital:.2f}")
                print(f"🎯 SL: {position['sl']:.2f} | TP: {position['tp']:.2f} | PnL: {pnl_live:.2f}")
                last_printed_pnl = pnl_live
                last_printed_price = current

            app.update_live_trade_pnl(pnl_live)
            app.live_pnl = pnl_live

            # --- Teilverkauf (APC) ---
            if hasattr(app, "apc_enabled") and app.apc_enabled.get():
                try:
                    apc_rate = float(app.apc_rate.get())
                    apc_interval = int(app.apc_interval.get())
                    apc_min_profit = float(app.apc_min_profit.get())
                    if pnl_live > apc_min_profit and position["amount"] > 1:
                        to_close = position["amount"] * (apc_rate / 100)
                        if to_close < 1:
                            to_close = 1

                        size_close = to_close * position["leverage"] / entry
                        fee = current * size_close * FEE_RATE
                        gross_pnl = calculate_futures_pnl(
                            entry,
                            current,
                            position["leverage"],
                            to_close,
                            position["side"],
                        )
                        realized = gross_pnl - fee
                        old_cap = capital
                        capital += realized
                        check_plausibility(realized, old_cap, capital, to_close)
                        position["amount"] -= to_close

                        log_msg = (
                            f"⚡️ Teilverkauf {to_close:.2f} | Entry {entry:.2f} -> "
                            f"Exit {current:.2f} | PnL {realized:.2f}$ | "
                            f"Balance {old_cap:.2f}->{capital:.2f} | Rest {position['amount']:.2f}"
                        )
                        app.log_event(log_msg)
                        app.apc_status_label.config(text=log_msg, foreground="blue")
                        if trader and live_trading:
                            live_partial_close(trader, settings["symbol"], position["side"], to_close)
                        if position["amount"] <= 0:
                            position = None
                            entry_time_global = None
                            app.log_event("✅ Position durch APC komplett geschlossen")
                            continue
                        time.sleep(apc_interval)
                except Exception as e:
                    print("❌ Fehler bei Auto Partial Close:", e)

            hit_tp = current >= position["tp"] if position["side"] == "long" else current <= position["tp"]
            hit_sl = current <= position["sl"] if position["side"] == "long" else current >= position["sl"]

            if hit_tp or hit_sl:
                gross_pnl = calculate_futures_pnl(
                    entry,
                    current,
                    position["leverage"],
                    position["amount"],
                    position["side"],
                )
                size_close = position["amount"] * position["leverage"] / entry
                fee = current * size_close * FEE_RATE
                pnl = gross_pnl - fee
                duration = int(now - position["entry_time"])
                old_cap = capital
                capital += pnl
                check_plausibility(pnl, old_cap, capital, position["amount"])

                # Risk-Manager informieren
                risk_manager.update_loss(pnl)

                

                app.update_pnl(pnl)
                app.update_capital(capital)
                log_msg = (
                    f"💥 Position geschlossen ({position['side']}) | Entry {entry:.2f} -> Exit {current:.2f} | PnL {pnl:.2f}"
                )
                print(log_msg)
                app.log_event(log_msg)
                print(f"💰 Aktuelles Balance: ${capital:.2f}")

                app.update_live_trade_pnl(0.0)
                app.live_pnl = 0.0

                if hit_sl:
                    cooldown.register_sl(time.time())

                position = None
                entry_time_global = None

            no_signal_printed = False
            continue  # Next Loop

        # --- ENTRY PLACEMENT ---
        if not position:
            if cooldown.in_cooldown(now):
                print("🕒 In Cooldown nach SL")
                time.sleep(1)
                continue
            if entry_type:
                no_signal_printed = False
                entry = candle["close"]
                now = time.time()
                amount = min(capital, float(gui_bridge.capital))

                sl, tp = None, None
                if entry_type in ["long", "short"]:
                    sl, tp = adaptive_sl.get_adaptive_sl_tp(
                        entry_type, entry, candles, tp_multiplier=tp_mult
                    )
                if sl is None or tp is None:
                    atr = candle["high"] - candle["low"]
                    sl = entry - atr * sl_mult if entry_type == "long" else entry + atr * sl_mult
                    tp = entry + atr * tp_mult if entry_type == "long" else entry - atr * tp_mult

                position = {
                    "side": entry_type,
                    "entry": entry,
                    "entry_time": now,
                    "sl": sl,
                    "tp": tp,
                    "amount": amount,
                    "initial_amount": amount,
                    "leverage": leverage,
                }

                entry_fee = amount * leverage * FEE_RATE
                if entry_fee > 0:
                    old_cap = capital
                    capital -= entry_fee
                    app.log_event(
                        f"💸 Entry Fee {entry_fee:.2f}$ | Balance {old_cap:.2f} -> {capital:.2f}"
                    )
                position_global = position
                entry_time_global = now
                app.position = position
                last_signal = entry_type
                last_signal_time = now

                stamp = datetime.now().strftime("%H:%M:%S")
                trade_msg = (
                    f"[{stamp}] Trade platziert: {entry_type.upper()} ({entry:.2f})"
                )
                print(trade_msg)
                if hasattr(app, "log_event"):
                    app.log_event(trade_msg)

                print(f"{'🟢' if entry_type == 'long' else '🔴'} {entry_type.upper()} Entry erkannt!")
                print_entry_status(position, capital, app, leverage, settings)



                if amount > 0 and trader and live_trading:
                    try:
                        direction = "BUY" if entry_type == "long" else "SELL"
                        trader.place_order(
                            settings["symbol"],
                            direction,
                            amount,
                            entry,
                            sl,
                            tp
                        )
                        trader.place_sl_tp_orders(
                            settings["symbol"],
                            direction,
                            entry,
                            sl,
                            tp,
                            amount
                        )
                    except Exception as e:
                        print(f"❌ Fehler bei Orderplatzierung: {e}")
            else:
                if not no_signal_printed:
                    print("➖ Kein Signal")
                    no_signal_printed = True

    reason = "Kapital aufgebraucht" if capital <= 0 else "Loop beendet"
    print_stop_banner(reason)
