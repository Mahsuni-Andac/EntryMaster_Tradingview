# console_status.py
#
# Changelog:
# - Added `print_stop_banner` for unified bot termination output

import time
from datetime import datetime

# ---- Rate-Limit Speicher für Warnungen ----
_last_warnings = {}
_last_options_snapshot = {}

def _throttle_warn(key, seconds=30):
    now = time.time()
    last = _last_warnings.get(key, 0)
    if now - last > seconds:
        _last_warnings[key] = now
        return True
    return False

def print_full_filter_overview(settings):
    """
    Gibt eine Übersicht aller Filter und Optionen mit Status (grüner Haken / rotes Kreuz) aus.
    """
    groups = [
        ("RSI", settings.get("rsi_filter", False)),
        ("Volume", settings.get("volume_filter", False)),
        ("EMA", settings.get("ema_filter", False)),
        ("SmartCooldown", settings.get("smart_cooldown", False)),
        ("TrailingSL", settings.get("trailing_sl", False)),
        ("Doji", settings.get("doji_filter", False)),
        ("Session", settings.get("session_filter", False)),
        ("Engulfing", settings.get("engulfing_filter", False)),
        ("BigMove", settings.get("big_move_filter", False)),
        ("Breakout", settings.get("breakout_filter", False)),
        ("TimeFilter", settings.get("time_filter", False)),
        ("ATR-Filter", settings.get("atr_filter", False)),
        ("Momentum", settings.get("momentum_filter", False)),
        ("Wick", settings.get("wick_filter", False)),
        ("Rejection", settings.get("rejection_filter", False)),
        ("ReEntry", settings.get("reentry_filter", False)),
        ("SL-Intelligenz", settings.get("sl_intel", False)),
        ("CapitalSafe", settings.get("capital_safe", False)),
        ("LiveMode", not settings.get("test_mode", True)),
        ("SimMode", settings.get("test_mode", False)),
        ("SessionBlock", settings.get("session_block", False)),
        ("SignalEngine", settings.get("signal_engine", False)),
        ("EntryMaster", settings.get("entry_master", False)),
        ("AdaptiveSL", settings.get("adaptive_sl", False)),
    ]
    print("🛠 Filter- & Optionen-Status:")
    for i, (name, active) in enumerate(groups):
        status = "✅" if active else "❌"
        print(f"{name:16}: {status}", end="   ")
        if (i + 1) % 4 == 0:
            print("")
    print("\n")

def options_snapshot(settings):
    """
    Liefert einen Hash/Snapshot der wichtigsten Einstellungen für Change-Detection.
    """
    keys = (
        "rsi_filter", "volume_filter", "ema_filter", "smart_cooldown", "trailing_sl",
        "doji_filter", "session_filter", "engulfing_filter", "big_move_filter",
        "breakout_filter", "time_filter", "atr_filter", "momentum_filter", "wick_filter",
        "rejection_filter", "reentry_filter", "sl_intel", "capital_safe", "test_mode",
        "session_block", "signal_engine", "entry_master", "adaptive_sl"
    )
    return tuple(settings.get(k) for k in keys)

def print_no_signal_status(settings, position=None, price=None, session_name=None, saved_profit=None, only_active_filters=True):
    """
    Gibt den 'Kein Signal' Statusblock mit Zeit und Session aus.
    """
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    print(f"{nowstr} ➖ Kein Signal" + (f" | Session: {session_name}" if session_name else ""))
    # Aktive Filter oder alle anzeigen
    filter_status = []
    filter_status.append("RSI✅" if settings.get("rsi_filter", False) else "RSI❌")
    filter_status.append("Volume✅" if settings.get("volume_filter", False) else "Volume❌")
    filter_status.append("EMA✅" if settings.get("ema_filter", False) else "EMA❌")
    filter_status.append("SmartCooldown✅" if settings.get("smart_cooldown", False) else "SmartCooldown❌")
    filter_status.append("TrailingSL✅" if settings.get("trailing_sl", False) else "TrailingSL❌")
    filter_status.append("Doji✅" if settings.get("doji_filter", False) else "Doji❌")
    filter_status.append("Session✅" if settings.get("session_filter", False) else "Session❌")
    filter_status.append("Engulfing✅" if settings.get("engulfing_filter", False) else "Engulfing❌")
    filter_status.append("BigMove✅" if settings.get("big_move_filter", False) else "BigMove❌")
    filter_status.append("Breakout✅" if settings.get("breakout_filter", False) else "Breakout❌")
    filter_status.append("TimeFilter✅" if settings.get("time_filter", False) else "TimeFilter❌")
    filter_status.append("ATR-Filter✅" if settings.get("atr_filter", False) else "ATR-Filter❌")
    filter_status.append("Momentum✅" if settings.get("momentum_filter", False) else "Momentum❌")
    filter_status.append("Wick✅" if settings.get("wick_filter", False) else "Wick❌")
    filter_status.append("Rejection✅" if settings.get("rejection_filter", False) else "Rejection❌")
    filter_status.append("ReEntry✅" if settings.get("reentry_filter", False) else "ReEntry❌")
    filter_status.append("SL-Intelligenz✅" if settings.get("sl_intel", False) else "SL-Intelligenz❌")
    filter_status.append("CapitalSafe✅" if settings.get("capital_safe", False) else "CapitalSafe❌")
    filter_status.append("LiveMode✅" if not settings.get("test_mode", True) else "LiveMode❌")
    filter_status.append("SimMode✅" if settings.get("test_mode", False) else "SimMode❌")
    filter_status.append("SessionBlock✅" if settings.get("session_block", False) else "SessionBlock❌")
    filter_status.append("SignalEngine✅" if settings.get("signal_engine", False) else "SignalEngine❌")
    filter_status.append("EntryMaster✅" if settings.get("entry_master", False) else "EntryMaster❌")
    filter_status.append("AdaptiveSL✅" if settings.get("adaptive_sl", False) else "AdaptiveSL❌")

    if only_active_filters:
        active = [f.replace("✅", "") for f in filter_status if "✅" in f]
        filters_text = " | ".join(active) if active else "Keine aktiven Filter"
        print("🎛 Aktive Filter:", filters_text)
    else:
        print("🎛 Filter/Optionen:", " | ".join(filter_status))

    sl = tp = "-"
    if position:
        sl = f"{position.get('sl', '-'):.2f}" if position.get('sl') is not None else "-"
        tp = f"{position.get('tp', '-'):.2f}" if position.get('tp') is not None else "-"
    balance = settings.get("starting_balance", "-")
    leverage = settings.get("leverage", "-")
    symbol = settings.get("symbol", "-")
    if price is None:
        price = "-"
    print(f"💵 Balance: {balance} | 💎 Gespart: {saved_profit if saved_profit is not None else '-'} | 📈 {symbol} Preis: {price} | 🎯 SL: {sl} | TP: {tp} | Lev: x{leverage}")
    print("")

def print_entry_status(position, settings):
    direction = position.get("direction", position.get("side", "?"))
    entry = position.get("entry", "-")
    sl = position.get("sl", "-")
    tp = position.get("tp", "-")
    symbol = position.get("symbol", settings.get("symbol", "-"))
    print(f"🚀 {symbol} ENTRY ({direction.upper()}): Entry {entry} | SL {sl} | TP {tp}")
    print("")

def print_position_status(position, price, session_name=None):
    direction = position.get("direction", position.get("side", "?"))
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    session_txt = f" | Session: {session_name}" if session_name else ""
    print(f"{nowstr} ⏳ Position offen ({direction}) | Entry: {position['entry']:.2f} | Now: {price:.2f}{session_txt}")
    print(f"🎯 SL: {position['sl']:.2f} | TP: {position['tp']:.2f}")
    print("")

def print_pnl_status(pnl, balance=None, saved=None):
    msg = f"📉 PnL: {pnl:.2f} $"
    if balance is not None:
        msg += f" | 💰 Balance: {balance:.2f}"
    if saved is not None:
        msg += f" | 💎 Gespart: {saved:.2f}"
    print(msg)
    print("")

def print_trade_closed(position, price, pnl, saved_profit=None, duration=None, session_name=None):
    direction = position.get("direction", position.get("side", "?")).upper()
    symbol = position.get("symbol", "-")
    entry = position.get("entry", "-")
    sl = position.get("sl", "-")
    tp = position.get("tp", "-")
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    session_txt = f" | Session: {session_name}" if session_name else ""
    print(f"{nowstr} 💥 Trade EXIT ({direction}) {symbol}")
    print(f"Entry: {entry} | Exit: {price} | SL: {sl} | TP: {tp}")
    print(f"📉 Gewinn: {pnl:+.2f} $ | 💎 Gespart: {saved_profit if saved_profit is not None else '-'}"
          + (f" | Dauer: {duration}min" if duration else "") + session_txt)
    print("")

def print_error(msg, exception=None):
    print(f"❌ Fehler: {msg}")
    if exception:
        print(str(exception))
    print("")

def print_warning(msg, warn_key="default", seconds=30):
    if _throttle_warn(warn_key, seconds):
        print(f"⚠️ {msg}")
        print("")

def print_info(msg):
    print(f"ℹ️ {msg}")
    print("")

def print_start_banner(mode, start_balance, saved_profit=None):
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    print(f"{nowstr} 🚀 Bot gestartet im {'Live' if mode=='live' else 'Sim'}-Modus")
    print(f"🧾 Startkapital: ${start_balance:.2f}" +
          (f" | 💎 Gespart: {saved_profit}" if saved_profit else ""))
    print("")

def print_stop_banner(reason: str | None = None) -> None:
    """Print a unified stop banner."""
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    msg = f"{nowstr} 🛑 Bot gestoppt"
    if reason:
        msg += f" – {reason}"
    print(msg)
    print("")

def print_settings_overview(settings):
    print_full_filter_overview(settings)

def print_sl_tp_distance_warning():
    print_warning("SL/TP Abstand zu klein – Trade ignoriert", warn_key="sl_tp_distance", seconds=30)
