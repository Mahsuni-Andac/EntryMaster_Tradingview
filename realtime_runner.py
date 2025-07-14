# realtime_runner.py

import os
import time
import traceback
from datetime import datetime
import logging
import data_provider
import queue
from requests.exceptions import RequestException
from tkinter import messagebox

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

from data_provider import (
    fetch_latest_candle,
    fetch_last_price,
    get_last_candle_time,
    get_live_candles,
    start_candle_websocket,
    get_candle_queue,
)
from config import BINANCE_INTERVAL, BINANCE_SYMBOL
from entry_handler import open_position
from exit_handler import close_position
from cooldown_manager import CooldownManager
from session_filter import get_global_filter
from status_block import print_entry_status
from gui_bridge import GUIBridge
from trading_gui_core import TradingGUI
from trading_gui_logic import TradingGUILogicMixin
from config import SETTINGS
from global_state import (
    entry_time_global,
    ema_trend_global,
    atr_value_global,
    position_global,
)
import global_state

from indicator_utils import calculate_ema, calculate_atr

from andac_entry_master import AndacEntryMaster, AndacSignal
from signal_worker import SignalWorker
from entry_logic import should_enter
from adaptive_sl_manager import AdaptiveSLManager


def update_indicators(candles):
    atr = calculate_atr(candles, 14)
    close_list = [c["close"] for c in candles[-20:] if "close" in c]
    ema = calculate_ema(close_list, 20)
    return atr, ema


def handle_existing_position(position, candle, app, capital, live_trading,
                             cooldown, risk_manager, last_printed_pnl,
                             last_printed_price, settings, now):
    current = candle["close"]
    entry = position["entry"]
    pnl_live = calculate_futures_pnl(
        entry,
        current,
        position["leverage"],
        position["amount"],
        position["side"],
    )

    if (
        last_printed_pnl is None
        or last_printed_price is None
        or abs(pnl_live - last_printed_pnl) > 1.0
        or abs(current - last_printed_price) > 1.0
    ):
        logging.info(
            "⏳ Position offen (%s) | Entry: %.2f | Now: %.2f",
            position["side"],
            entry,
            current,
        )
        logging.info(
            "🎯 SL: %.2f | TP: %.2f | PnL: %.2f",
            position["sl"],
            position["tp"],
            pnl_live,
        )
        last_printed_pnl = pnl_live
        last_printed_price = current

    app.update_live_trade_pnl(pnl_live)
    app.live_pnl = pnl_live

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
                if live_trading:
                    live_partial_close(position["side"], to_close)
                if position["amount"] <= 0:
                    position = None
                    entry_time_global = None
                    app.log_event("✅ Position durch APC komplett geschlossen")
                    return position, capital, last_printed_pnl, last_printed_price, True
                time.sleep(apc_interval)
        except Exception as e:
            logging.error("Fehler bei Auto Partial Close: %s", e)

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
        old_cap = capital
        capital += pnl
        check_plausibility(pnl, old_cap, capital, position["amount"])

        risk_manager.update_loss(pnl)

        app.update_pnl(pnl)
        app.update_capital(capital)
        log_msg = (
            f"💥 Position geschlossen ({position['side']}) | Entry {entry:.2f} -> Exit {current:.2f} | PnL {pnl:.2f}"
        )
        logging.info(log_msg)
        app.log_event(log_msg)
        if live_trading:
            close_position()

        app.update_live_trade_pnl(0.0)
        app.live_pnl = 0.0

        if hit_sl:
            cooldown.register_sl(time.time())

        position = None
        entry_time_global = None

    return position, capital, last_printed_pnl, last_printed_price, False

from risk_manager import RiskManager
from console_status import (
    print_start_banner,
    print_stop_banner,
    print_warning,
    print_info,
)
from pnl_utils import calculate_futures_pnl, check_plausibility

FEE_RATE = 0.0004

gui_bridge = None

def live_partial_close(side: str, qty: float) -> None:
    reduce_side = "SELL" if side == "long" else "BUY"
    res = open_position(reduce_side, qty, reduce_only=True)
    if res is not None:
        print(f"⚡️ LIVE-Teilschließung: {qty} {reduce_side} via Reduce Only Market")
    else:
        print("❌ Fehler beim Live-Teilverkauf")

def set_gui_bridge(gui_instance):
    global gui_bridge
    gui_bridge = GUIBridge(gui_instance)

def cancel_trade(position, app):
    print(f"❌ Abbruch der Position: {position['side']} @ {position['entry']:.2f}")
    app.position = None
    app.log_event("🛑 Position wurde durch Benutzer abgebrochen!")
    return None

def emergency_exit_position(app):
    if app.position:
        print("❗️ Notausstieg ausgelöst! Die Position wird geschlossen.")
        cancel_trade(app.position, app)
        app.log_event("🛑 Position wurde im Notausstiegsmodus geschlossen!")
    else:
        print("❌ Keine Position offen, um sie zu schließen!")
        app.log_event(
            "❌ Keine offene Position zum Notausstiegsmodus gefunden."
        )


def wait_for_initial_candles(
    app: TradingGUILogicMixin | TradingGUI | None = None,
    required: int = 14,
    timeout: int = 20,
) -> list[dict]:

    start_time = time.time()
    last_logged = -1

    while True:
        candles = get_live_candles(required)
        count = len(candles)
        if count >= required:
            msg = "✅ ATR bereit – Starte Bot-Logik."
            logging.info(msg)
            if app and hasattr(app, "update_status"):
                app.update_status(msg)
            else:
                gui_bridge.update_status(msg)
            return candles

        elapsed = time.time() - start_time
        if elapsed >= timeout:
            msg = (
                f"⚠️ Timeout beim Warten auf Candles – starte trotzdem ({count}/{required})"
            )
            logging.warning(msg)
            if app and hasattr(app, "update_status"):
                app.update_status(msg)
            else:
                gui_bridge.update_status(msg)
            return candles

        if count != last_logged:
            progress = (
                f"⏳ Warte auf ATR-Berechnung... ({count}/{required} Candles erhalten)"
            )
            logging.info(progress)
            if app and hasattr(app, "update_status"):
                app.update_status(progress)
            else:
                gui_bridge.update_status(progress)
            last_logged = count
        time.sleep(1)

def _run_bot_live_inner(settings=None, app=None):
    global entry_time_global, position_global, ema_trend_global, atr_value_global

    capital = SETTINGS.get("starting_capital", 1000)
    start_capital = capital

    print_start_banner(capital)

    interval_setting = settings.get("interval", BINANCE_INTERVAL)
    if not data_provider._CANDLE_WS_STARTED:
        start_candle_websocket(interval_setting)
    else:
        logging.info("Candle WebSocket already running")

    if app:
        settings["log_event"] = app.log_event
        set_gui_bridge(app)
        start_capital = capital
        if hasattr(app, "sl_tp_status_var"):
            app.sl_tp_status_var.set("")
    
    risk_manager = RiskManager(app, start_capital)
    cfg = {}
    for key in ("max_loss", "max_drawdown", "max_trades"):
        if key in settings:
            cfg[key] = settings[key]
    if cfg:
        risk_manager.configure(**cfg)

    multiplier = gui_bridge.multiplier
    capital = float(gui_bridge.capital)
    start_capital = capital
    interval = interval_setting
    auto_multi = gui_bridge.auto_multiplier

    ATR_REQUIRED = 14
    candles_ready = wait_for_initial_candles(app, ATR_REQUIRED)
    atr_tmp = calculate_atr(candles_ready, ATR_REQUIRED)
    atr_value_global = atr_tmp
    if app and hasattr(app, "update_status"):
        app.update_status("✅ Bereit")
    else:
        gui_bridge.update_status("✅ Bereit")

    live_requested = gui_bridge.live_trading
    paper_mode = settings.get("paper_mode", True)
    live_trading = live_requested and not paper_mode
    settings["paper_mode"] = not live_trading

    leverage = multiplier

    cooldown = CooldownManager(settings.get("cooldown", 3))
    session_filter = get_global_filter(settings.get("session_filter"))

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

    def process_candle(candle: dict) -> None:
        nonlocal candles, position, capital, last_printed_pnl, last_printed_price, last_signal, last_signal_time, no_signal_printed
        candles.append(candle)
        if len(candles) > 100:
            candles.pop(0)

        atr_value, ema = update_indicators(candles)
        atr_value_global = atr_value
        settings["ema_value"] = ema

        if ema is not None:
            ema_trend_global = "⬆️" if candle["close"] > ema else "⬇️"
        else:
            ema_trend_global = "❓"

        close_price = candle["close"]
        now = time.time()

        if settings.get("use_session_filter") and not session_filter.is_allowed():
            return

        if hasattr(app, "auto_apply_recommendations") and app.auto_apply_recommendations.get():
            try:
                app.apply_recommendations()
            except Exception as e:
                logging.error("Auto recommendation failed: %s", e)

        andac_signal: AndacSignal = should_enter(candle, andac_indicator)
        entry_type = andac_signal.signal
        stamp = datetime.now().strftime("%H:%M:%S")
        if entry_type:
            msg = f"[{stamp}] Signal erkannt: {entry_type.upper()} ({BINANCE_SYMBOL} @ {close_price:.2f})"
            logging.info(msg)
            if hasattr(app, "log_event"):
                app.log_event(msg)
        elif andac_signal.reasons:
            reason_msg = ", ".join(andac_signal.reasons)
            msg = f"[{stamp}] Signal verworfen: {reason_msg}"
            logging.info(msg)
            if hasattr(app, "log_event"):
                app.log_event(msg)

        if position:
            position_data = handle_existing_position(
                position,
                candle,
                app,
                capital,
                live_trading,
                cooldown,
                risk_manager,
                last_printed_pnl,
                last_printed_price,
                settings,
                now,
            )
            position, capital, last_printed_pnl, last_printed_price, closed = position_data
            if closed:
                return
            no_signal_printed = False
            return

        if not position:
            if cooldown.in_cooldown(now):
                return
            if entry_type:
                no_signal_printed = False
                entry = candle["close"]
                amount = min(capital, float(gui_bridge.capital))
                sl = tp = None

                if gui_bridge.manual_active:
                    sl = gui_bridge.manual_sl
                    tp = gui_bridge.manual_tp
                    if sl is None or tp is None:
                        gui_bridge.set_manual_status(False)
                        sl = tp = None
                    else:
                        valid = sl < entry and tp > entry if entry_type == "long" else sl > entry and tp < entry
                        if valid:
                            gui_bridge.set_manual_status(True)
                        else:
                            gui_bridge.set_manual_status(False)
                            sl = tp = None

                if sl is None and tp is None and gui_bridge.auto_active:
                    try:
                        sl, tp = adaptive_sl.get_adaptive_sl_tp(entry_type, entry, candles, tp_multiplier=tp_mult)
                        valid = (sl < entry and tp > entry) if entry_type == "long" else (sl > entry and tp < entry)
                        if not valid:
                            gui_bridge.set_auto_status(False)
                            sl = tp = None
                    except Exception as e:
                        logging.error("Adaptive SL Fehler: %s", e)
                        gui_bridge.set_auto_status(False)
                        sl = tp = None

                if sl is None or tp is None:
                    return

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
                    capital -= entry_fee
                    app.log_event(f"💸 Entry Fee {entry_fee:.2f}$")

                position_global = position
                entry_time_global = now
                app.position = position
                last_signal = entry_type
                last_signal_time = now

                msg = f"[{stamp}] Trade platziert: {entry_type.upper()} ({entry:.2f})"
                logging.info(msg)
                if hasattr(app, "log_event"):
                    app.log_event(msg)

                if amount > 0 and live_trading:
                    try:
                        direction = "BUY" if entry_type == "long" else "SELL"
                        res = open_position(direction, amount)
                        if res is None:
                            raise RuntimeError("Order placement failed")
                    except Exception as e:
                        logging.error("Orderplatzierung fehlgeschlagen: %s", e)
            else:
                if not no_signal_printed:
                    logging.info("➖ Ich warte auf ein Indikator Signal")
                    no_signal_printed = True

    candle_queue = get_candle_queue()
    worker = SignalWorker(process_candle)
    worker.start()

    while capital > 0 and not getattr(app, "force_exit", False):
        if not worker.is_alive():
            worker.start()
        if not getattr(app, "running", False):
            time.sleep(1)
            continue
        if not getattr(app, "feed_ok", True):
            print(
                f"🧪 Letzter Feed-Eingang vor {time.time() - global_state.last_feed_time:.1f} Sekunden"
            )
            time.sleep(1)
            continue
        risk_manager.update_capital(capital)
        if risk_manager.check_loss_limit() or risk_manager.check_drawdown_limit():
            time.sleep(1)
            continue

        try:
            candle = candle_queue.get(timeout=1)
        except queue.Empty:
            continue
        try:
            stamp = datetime.now().strftime("%H:%M:%S")
            candle_warning_printed = False

            if not all(
                k in candle and candle[k] is not None
                for k in ("open", "high", "low", "close", "volume")
            ):
                print("⚠️ Candle-Daten unvollständig oder fehlerhaft", candle)
                time.sleep(1)
                continue

            if not first_feed:
                first_feed = True
                if hasattr(app, "log_event"):
                    app.log_event("✅ Erster Marktdaten-Feed empfangen")

            worker.submit(candle)
            continue

        except Exception as e:
            print("❌ Fehler im Botlauf:", e)
            traceback.print_exc()
            time.sleep(2)
            continue

    reason = "Kapital aufgebraucht" if capital <= 0 else "Loop beendet"
    print_stop_banner(reason)

def run_bot_live(settings=None, app=None):
    """Wrapper for _run_bot_live_inner with error handling."""
    try:
        _run_bot_live_inner(settings, app)
    except RequestException:
        if app:
            messagebox.showerror(
                "Startfehler",
                "❌ API-Zugang ungültig oder Server nicht erreichbar.",
            )
        logging.error("API error during bot start", exc_info=True)
    except (KeyError, ValueError) as exc:
        if app:
            messagebox.showerror("Startfehler", f"❌ Konfigurationsfehler: {exc}")
        logging.error("Configuration error during bot start", exc_info=True)
    except Exception as exc:
        if app:
            messagebox.showerror("Startfehler", f"❌ Botstart fehlgeschlagen: {exc}")
        logging.error("Unexpected error during bot start", exc_info=True)
