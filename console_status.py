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
    """Ausgabe des aktuellen Betriebsmodus."""
    print("🛠 Andac Entry-Master aktiviert")

def options_snapshot(settings):
    """Liefer einen einfachen Snapshot für Reload-Checks."""
    return tuple(settings.get(k) for k in sorted(settings.keys()))

def print_no_signal_status(settings, position=None, price=None, session_name=None, saved_profit=None, only_active_filters=True):
    """
    Gibt den 'Kein Signal' Statusblock mit Zeit und Session aus.
    """
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    print(f"{nowstr} ➖ Kein Signal" + (f" | Session: {session_name}" if session_name else ""))
    print("🎛 Andac Entry-Master aktiv")

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
