# realtime_runner.py
# -*- coding: utf-8 -*-

import os
import time
import traceback
from datetime import datetime
import logging
import queue
import random
import data_provider
from requests.exceptions import RequestException
from tkinter import messagebox

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def now_time() -> str:
    """Return the current time formatted as HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")

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
from exit_handler import close_position, close_partial_position
from cooldown_manager import CooldownManager
from status_block import print_entry_status
from gui_bridge import GUIBridge
from trading_gui_core import TradingGUI
from trading_gui_logic import TradingGUILogicMixin
from config import SETTINGS
from central_logger import log_triangle_signal
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
from status_events import StatusDispatcher


# TIMEFILTER: GUI based time window check
def is_within_active_timeframe(gui) -> bool:
    if not gui.use_time_filter.get():
        return True
    now = datetime.now().time()
    for start_var, end_var in getattr(gui, "time_filters", []):
        try:
            start = datetime.strptime(start_var.get(), "%H:%M").time()
            end = datetime.strptime(end_var.get(), "%H:%M").time()
            if start <= now <= end:
                return True
        except ValueError:
            continue
    return False


def update_indicators(candles):
    atr = calculate_atr(candles, 14)
    closes = [c["close"] for c in candles if "close" in c]
    ema = calculate_ema(closes[-20:], 20)
    rsi = AndacEntryMaster._rsi(closes, 14)
    return atr, ema, rsi


def handle_existing_position(position, candle, app, capital, live_trading,
                             cooldown, risk_manager, last_printed_pnl,
                             last_printed_price, settings, now,
                             signal=None, current_index=None):
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
        sl_val = position.get("sl")
        tp_val = position.get("tp")

        if isinstance(sl_val, (int, float)) and isinstance(tp_val, (int, float)):
            logging.info(
                "🎯 SL: %.2f | TP: %.2f | PnL: %.2f",
                sl_val,
                tp_val,
                pnl_live,
            )
        else:
            logging.warning(
                "🎯 SL/TP fehlen – SL: %s | TP: %s | PnL: %.2f",
                sl_val,
                tp_val,
                pnl_live,
            )
        last_printed_pnl = pnl_live
        last_printed_price = current

    app.update_live_trade_pnl(pnl_live)
    app.live_pnl = pnl_live

    tp_price = position.get("tp")
    if (
        settings.get("auto_partial_close", False)
        and tp_price is not None
        and not position.get("partial_closed", False)
    ):
        hit_tp = (
            current >= tp_price
            if position["side"] == "long"
            else current <= tp_price
        )
        if hit_tp:
            partial_volume = position.get("amount", 0) * 0.5
            result = close_partial_position(partial_volume) if live_trading else True
            if result:
                _, realized = _basic_simulate_trade(
                    entry,
                    position["side"],
                    tp_price,
                    partial_volume,
                    position["leverage"],
                    FEE_MODEL,
                )
                old_cap = capital
                capital += realized
                check_plausibility(realized, old_cap, capital, partial_volume)
                position["amount"] -= partial_volume
                position["partial_closed"] = True
                app.log_event(
                    f"⚡ Auto Partial Close bei TP ausgelöst! ➖ {partial_volume} Kontrakte glattgestellt."
                )
            else:
                app.log_event("⚠️ Fehler beim Partial Close!")

    if hasattr(app, "apc_enabled") and app.apc_enabled.get():
        try:
            apc_rate = float(app.apc_rate.get())
            apc_interval = int(app.apc_interval.get())
            apc_min_profit = float(app.apc_min_profit.get())
            if pnl_live > apc_min_profit and position["amount"] > 1:
                to_close = position["amount"] * (apc_rate / 100)
                if to_close < 1:
                    to_close = 1

                _, realized = _basic_simulate_trade(
                    entry,
                    position["side"],
                    current,
                    to_close,
                    position["leverage"],
                    FEE_MODEL,
                )
                old_cap = capital
                capital += realized
                check_plausibility(realized, old_cap, capital, to_close)
                position["amount"] -= to_close

                log_msg = (
                    f"⚡️ Teilverkauf {to_close:.2f} | Entry {entry:.2f} -> "
                    f"Exit {exit_price:.2f} | PnL {realized:.2f}$ | "
                    f"Balance {old_cap:.2f}->{capital:.2f} | Rest {position['amount']:.2f}"
                )
                app.log_event(log_msg)
                app.apc_status_label.config(text=log_msg, foreground="blue")
                if live_trading:
                    live_partial_close(position["side"], to_close)
                if position["amount"] <= 0:
                    position = None
                    position_open = False
                    entry_time_global = None
                    app.log_event("✅ Position durch APC komplett geschlossen")
                    return position, capital, last_printed_pnl, last_printed_price, True
                time.sleep(apc_interval)
        except Exception as e:
            logging.error("Fehler bei Auto Partial Close: %s", e)

    tp_price = position.get("tp")
    sl_price = position.get("sl")

    high = candle.get("high", current)
    low = candle.get("low", current)

    hit_tp = False
    hit_sl = False
    exit_price = current

    timed_exit = False
    hold_duration = 0
    if (
        not live_trading
        and current_index is not None
        and position.get("entry_index") is not None
    ):
        hold_duration = current_index - position["entry_index"]
        if hold_duration >= MAX_HOLD_CANDLES:
            timed_exit = True

    if tp_price is None or sl_price is None:
        if timed_exit:
            logging.warning(
                "⚠️ SL/TP fehlen – Timed Exit nach %d Kerzen", MAX_HOLD_CANDLES
            )
            exit_price = candle["close"]
        else:
            logging.warning("SL/TP Werte fehlen, überspringe Positionsprüfung")
            if hasattr(app, "current_position") and app.current_position:
                app.current_position["bars_open"] = hold_duration
                if hasattr(app, "update_trade_display"):
                    app.update_trade_display()
            return position, capital, last_printed_pnl, last_printed_price, False
    else:
        if position["side"] == "long":
            if low <= sl_price:
                hit_sl = True
                exit_price = sl_price
            elif high >= tp_price:
                hit_tp = True
                exit_price = tp_price
        else:
            if high >= sl_price:
                hit_sl = True
                exit_price = sl_price
            elif low <= tp_price:
                hit_tp = True
                exit_price = tp_price

    if timed_exit and tp_price is None and sl_price is None:
        hit_tp = False
        hit_sl = False

    if hasattr(app, "current_position") and app.current_position:
        app.current_position["bars_open"] = hold_duration
        if hasattr(app, "update_trade_display"):
            app.update_trade_display()

    opp_exit = False
    if signal and signal in ("long", "short"):
        opp_exit = (
            (position["side"] == "long" and signal == "short") or
            (position["side"] == "short" and signal == "long")
        )

    should_close = hit_tp or hit_sl or timed_exit or opp_exit

    if should_close:
        new_capital = simulate_trade(
            position,
            exit_price,
            current_index if current_index is not None else 0,
            settings,
            capital,
        )
        pnl = new_capital - capital
        old_cap = capital
        capital = new_capital
        check_plausibility(pnl, old_cap, capital, position["amount"])

        risk_manager.update_loss(pnl)

        app.update_pnl(pnl)
        app.update_capital(capital)
        app.update_last_trade(position["side"], entry, exit_price, pnl)
        if hasattr(app, "current_position"):
            app.current_position = None
            if hasattr(app, "update_trade_display"):
                app.update_trade_display()

        if hit_tp:
            reason = "TP erreicht"
        elif hit_sl:
            reason = "SL erreicht"
        elif timed_exit:
            reason = (
                f"\u23F1 Timed Exit: {position['side'].upper()} @ {exit_price:.2f} "
                f"nach {hold_duration} Kerzen"
            )
        else:
            reason = "Gegensignal"

        if timed_exit:
            stamp = now_time()
            log_msg = f"[{stamp}] {reason}"
            logger.info(log_msg)
            logger.info(
                f"💰 Simuliertes Kapital: ${capital:.2f} | Realisierter PnL: {pnl:.2f}"
            )
        elif opp_exit:
            stamp = datetime.now().strftime("%H:%M:%S")
            log_msg = f"[{stamp}] {reason} bei {exit_price:.2f} | PnL {pnl:.2f}"
        else:
            log_msg = (
                f"\U0001F4A5 Position geschlossen ({position['side']}) | Entry {entry:.2f} -> Exit {exit_price:.2f} | PnL {pnl:.2f}"
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
        position_open = False
        entry_time_global = None
        return position, capital, last_printed_pnl, last_printed_price, True

    return position, capital, last_printed_pnl, last_printed_price, False

from risk_manager import RiskManager
from console_status import (
    print_start_banner,
    print_stop_banner,
    print_warning,
    print_info,
)
from pnl_utils import calculate_futures_pnl, check_plausibility
from simulator import FeeModel, simulate_trade as _basic_simulate_trade

# Maximum number of candles to keep a simulated trade open
MAX_HOLD_CANDLES = 10
FEE_MODEL = FeeModel(taker_fee=0.0004)
POSITION_SIZE = 1.0

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
    if hasattr(app, "current_position"):
        app.current_position = None
        if hasattr(app, "update_trade_display"):
            app.update_trade_display()
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

    if "track_history" not in settings:
        settings["track_history"] = True
        settings["trade_history"] = []

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
    leverage = multiplier
    live_requested = gui_bridge.live_trading
    paper_mode = settings.get("paper_mode", True)
    live_trading = live_requested and not paper_mode
    settings["paper_mode"] = not live_trading

    cooldown = CooldownManager(settings.get("cooldown", 3))
    # REMOVED: SessionFilter

    config = {
        "lookback": int(app.andac_lookback.get()),
        "puffer": float(app.andac_puffer.get()),
        "volumen_factor": float(app.andac_vol_mult.get()),
        "opt_rsi_ema": app.andac_opt_rsi_ema.get(),
        "opt_safe_mode": app.andac_opt_safe_mode.get(),
        "opt_engulf": app.andac_opt_engulf.get(),
        "opt_engulf_bruch": app.andac_opt_engulf_bruch.get(),
        "opt_engulf_big": app.andac_opt_engulf_big.get(),
        "opt_confirm_delay": app.andac_opt_confirm_delay.get(),
        "opt_mtf_confirm": app.andac_opt_mtf_confirm.get(),
        "opt_volumen_strong": app.andac_opt_volumen_strong.get(),
    }
    adaptive_sl = AdaptiveSLManager()

    candles = []
    position = None
    position_entry_index = None
    entry_price = None
    position_open = False
    current_position_direction = None
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
    previous_signal = None

    def process_candle(candle: dict) -> None:
        nonlocal candles, position, capital, last_printed_pnl, last_printed_price, \
                 last_signal, last_signal_time, no_signal_printed, first_feed, \
                 previous_signal, position_entry_index, entry_price, \
                 position_open, current_position_direction
        if not first_feed:
            first_feed = True
            if hasattr(app, "log_event"):
                app.log_event("✅ Erster Marktdaten-Feed empfangen")
        candles.append(candle)
        if len(candles) > 100:
            candles.pop(0)

        atr_value, ema, rsi_val = update_indicators(candles)
        atr_value_global = atr_value
        settings["ema_value"] = ema

        if ema is not None:
            ema_trend_global = "⬆️" if candle["close"] > ema else "⬇️"
        else:
            ema_trend_global = "❓"

        close_price = candle["close"]
        now = time.time()

        if not is_within_active_timeframe(app):
            logger.info("⏳ Außerhalb der Handelszeit – kein Entry erlaubt")
            time.sleep(1)
            return

        if hasattr(app, "auto_apply_recommendations") and app.auto_apply_recommendations.get():
            try:
                app.apply_recommendations()
            except Exception as e:
                logging.error("Auto recommendation failed: %s", e)

        lookback = config.get("lookback", 20)
        recent = candles[-(lookback + 1):]
        highs = [c["high"] for c in recent[:-1]]
        lows = [c["low"] for c in recent[:-1]]
        vols = [c.get("volume", 0.0) for c in recent[:-1]]
        avg_volume = sum(vols) / len(vols) if vols else candle.get("volume", 0.0)
        high_lb = max(highs) if highs else candle["high"]
        low_lb = min(lows) if lows else candle["low"]
        prev_close = recent[-2]["close"] if len(recent) > 1 else None
        prev_open = recent[-2]["open"] if len(recent) > 1 else None

        indicator = {
            "rsi": rsi_val,
            "atr": atr_value,
            "avg_volume": avg_volume,
            "high_lookback": high_lb,
            "low_lookback": low_lb,
            "prev_close": prev_close,
            "prev_open": prev_open,
            "mtf_ok": True,
            "prev_bull_signal": previous_signal == "long",
            "prev_baer_signal": previous_signal == "short",
        }

        andac_signal: AndacSignal = should_enter(candle, indicator, config)
        entry_type = andac_signal.signal
        previous_signal = entry_type
        stamp = datetime.now().strftime("%H:%M:%S")
        if entry_type:
            triangle_msg = log_triangle_signal(entry_type, close_price)
            if hasattr(app, "log_event"):
                app.log_event(triangle_msg)
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

        # Timed Exit Logic for simulation mode
        if not live_trading and position_open:
            hold_duration = len(candles) - 1 - position_entry_index
            if hold_duration >= MAX_HOLD_CANDLES:
                exit_price = candle["close"]
                direction = current_position_direction
                new_capital = simulate_trade(
                    position,
                    exit_price,
                    len(candles) - 1,
                    settings,
                    capital,
                )
                pnl = new_capital - capital
                capital = new_capital
                risk_manager.update_loss(pnl)
                app.update_pnl(pnl)
                app.update_capital(capital)
                app.update_last_trade(direction.lower(), entry_price, exit_price, pnl)
                if hasattr(app, "current_position"):
                    app.current_position = None
                    if hasattr(app, "update_trade_display"):
                        app.update_trade_display()
                position_open = False
                position = None
                app.position = None
                position_global = None
                entry_time_global = None
                logger.info(
                    f"[{now_time()}] \u23F1 Timed Exit: {direction} @ {exit_price:.2f} nach {hold_duration} Kerzen"
                )
                logger.info(
                    f"💰 Simuliertes Kapital: ${capital:.2f} | Realisierter PnL: {pnl:.2f}"
                )
                return

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
                entry_type,
                len(candles) - 1,
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
                slip = random.uniform(*FEE_MODEL.slippage_range)
                entry_exec = entry * (1 + slip) if entry_type == "long" else entry * (1 - slip)
                amount = capital * POSITION_SIZE
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
                        sl, tp = adaptive_sl.get_adaptive_sl_tp(
                            entry_type,
                            entry,
                            candles,
                            tp_multiplier=tp_mult,
                        )
                        valid = (
                            sl < entry and tp > entry
                            if entry_type == "long"
                            else sl > entry and tp < entry
                        )
                        if not valid:
                            raise ValueError("Ungültige SL/TP-Relation")
                    except Exception as e:
                        logging.error(
                            f"Adaptive SL Fehler – Fallback aktiviert: {e}"
                        )
                        if entry_type == "long":
                            sl = round(entry * 0.995, 2)
                            tp = round(entry * 1.01, 2)
                        else:
                            sl = round(entry * 1.005, 2)
                            tp = round(entry * 0.99, 2)
                    if sl is None or tp is None:
                        return

                position = {
                    "side": entry_type,
                    "entry": entry_exec,
                    "entry_time": now,
                    "entry_index": len(candles) - 1,
                    "sl": sl,
                    "tp": tp,
                    "amount": amount,
                    "initial_amount": amount,
                    "leverage": leverage,
                }

                entry_fee = amount * leverage * FEE_MODEL.taker_fee
                if entry_fee > 0:
                    capital -= entry_fee
                    app.log_event(f"💸 Entry Fee {entry_fee:.2f}$")

                position_global = position
                entry_time_global = now
                app.position = position
                app.current_position = {
                    "direction": entry_type.upper(),
                    "entry_price": entry_exec,
                    "entry_time": datetime.now(),
                    "bars_open": 0,
                }
                position_entry_index = len(candles) - 1
                entry_price = candle["close"]
                # === Manuelles SL/TP aus GUI anwenden, falls aktiv
                if settings.get("sl_tp_manual_active", False):
                    tp_val = settings.get("manual_tp", None)
                    sl_val = settings.get("manual_sl", None)
                    if tp_val:
                        position["tp"] = (
                            entry_price * (1 + tp_val / 100)
                            if entry_type == "long"
                            else entry_price * (1 - tp_val / 100)
                        )
                    if sl_val:
                        position["sl"] = (
                            entry_price * (1 - sl_val / 100)
                            if entry_type == "long"
                            else entry_price * (1 + sl_val / 100)
                        )
                    app.log_event(
                        f"🎯 Manuelles TP/SL gesetzt → TP: {position.get('tp', '–')} | SL: {position.get('sl', '–')}"
                    )
                position_open = True
                current_position_direction = entry_type.upper()
                last_signal = entry_type
                last_signal_time = now

                msg = f"[{stamp}] Trade platziert: {entry_type.upper()} ({entry_exec:.2f})"
                logging.info(msg)
                if hasattr(app, "log_event"):
                    app.log_event(msg)
                if hasattr(app, "update_trade_display"):
                    app.update_trade_display()

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
    worker = SignalWorker(process_candle, queue_obj=candle_queue)
    worker.start()

    if not data_provider._CANDLE_WS_STARTED:
        start_candle_websocket(interval_setting)
    else:
        logging.info("Candle WebSocket already running")

    preload = candle_queue.qsize()
    if preload:
        flush_limit = min(preload, 2)
        logging.info("\U0001F504 Clean Flush %s Candles", flush_limit)
        for _ in range(flush_limit):
            try:
                process_candle(candle_queue.get_nowait())
            except queue.Empty:
                break

    logging.info(
        "Candle-Worker gestartet (%s Candles im Buffer)", worker.queue.qsize()
    )

    ATR_REQUIRED = 14
    candles_ready = wait_for_initial_candles(app, ATR_REQUIRED)
    atr_tmp = calculate_atr(candles_ready, ATR_REQUIRED)
    atr_value_global = atr_tmp
    if app and hasattr(app, "update_status"):
        app.update_status("✅ Bereit")
    else:
        gui_bridge.update_status("✅ Bereit")

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
        backlog = worker.queue.qsize()
        if backlog > 5:
            if not candle_warning_printed:
                logging.warning("⚠️ Candle-Backlog > %s – mögliche Latenz!", backlog)
                StatusDispatcher.dispatch("feed", False, "Candle-Lag")
                candle_warning_printed = True
        else:
            if backlog == 0:
                StatusDispatcher.dispatch("feed", True)
            candle_warning_printed = False
        time.sleep(0.1)

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


def simulate_trade(position: dict, exit_price: float, candle_index: int,
                   settings: dict, capital: float) -> float:
    """Simulate a trade outcome and update capital/history."""

    fee_rate = settings.get("fee_percent", 0.04) / 100
    entry = position["entry"]
    qty = position["amount"]
    side = position["side"]
    leverage = position.get("leverage", 1)

    max_qty = (capital * leverage) / entry if entry else qty
    if qty > max_qty:
        logging.warning(
            "⚠️ Kontraktgröße reduziert: %.2f -> %.2f", qty, max_qty
        )
        qty = max_qty

    pnl = (exit_price - entry) if side == "long" else (entry - exit_price)
    pnl_value = pnl * qty * leverage

    fees = (entry + exit_price) * qty * fee_rate
    net_result = pnl_value - fees
    net_result = max(-capital, net_result)

    base = capital
    if base <= 0:
        logging.warning("⚠️ Kapital <= 0 – PnL-Berechnung kann ungenau werden")
        base = 1

    percent_change = (net_result / base) * 100

    direction = "LONG" if side == "long" else "SHORT"
    logging.info(
        f"[{time.strftime('%H:%M:%S')}] \U0001F4B0 Trade abgeschlossen: {direction} {entry:.2f} → {exit_price:.2f} | PnL: {net_result:.2f}$ ({percent_change:.2f}%)"
    )

    if settings.get("track_history"):
        settings.setdefault("trade_history", [])
        settings["trade_history"].append(
            {
                "time": time.strftime("%H:%M:%S"),
                "entry": entry,
                "exit": exit_price,
                "side": direction,
                "pnl": round(net_result, 2),
                "percent": round(percent_change, 2),
                "bars_open": candle_index - position.get("entry_index", 0),
            }
        )

    return capital + net_result
