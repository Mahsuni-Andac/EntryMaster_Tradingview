# status_block.py

import time
from datetime import datetime, timedelta
from colorama import Style
from global_state import atr_value_global, ema_trend_global  # Stelle sicher, dass ema_trend_global importiert ist

def get_entry_status_text(position: dict, capital, app, leverage: int, settings: dict) -> str:
    from datetime import timedelta
    from colorama import Style

    side = position["side"]
    color = "🟢" if side == "long" else "🔴"
    entry_time = position.get("entry_time")
    runtime = int(time.time() - entry_time) if entry_time else 0
    runtime_str = str(timedelta(seconds=runtime))
    now = datetime.now()
    uhrzeit = now.strftime("%H:%M:%S")
    datum = now.strftime("%d.%m.%Y")
    einsatz = float(position.get("amount", capital))
    entry_price = float(position["entry"])
    atr = float(atr_value_global) if atr_value_global is not None else 0.0
    ema_trend = ema_trend_global  # Verwende die globale ema_trend_global-Variable
    modus = "🧪 Modus: TEST" if settings.get("test_mode") else "🚀 Modus: LIVE"
    trade_info = f"{side.upper()} @ {entry_price:.2f}"
    pnl = 0.0  # Platzhalter

    # Leverage als x20, ohne Nachkommastellen wenn möglich
    lev_str = f"x{int(leverage)}" if leverage == int(leverage) else f"x{leverage:.2f}"

    # Filterstatus
    filters = {
        "RSI": app.use_rsi_filter.get(),
        "Vol": app.use_volume_filter.get(),
        "EMA": app.use_ema_filter.get(),
        "ENG": app.use_engulfing_filter.get(),
        "BIG": app.use_bigcandle_filter.get(),
        "BRK": app.use_breakout_filter.get(),
        "DOJI": app.use_doji_blocker.get(),
        "T-FLT": app.use_time_filter.get(),
        "SCool": app.use_smart_cooldown.get(),
    }
    filter_line = "🎛 Filter: " + "  ".join(f"{k}{'✅' if v else '❌'}" for k, v in filters.items())

    # SmartCooldown-Anzeige
    scool_line = ""
    if filters["SCool"] and hasattr(app, "smart_cooldown"):
        rem_fn = getattr(app.smart_cooldown, 'get_remaining_cooldown', None)
        if callable(rem_fn):
            remaining = rem_fn()
            if remaining > 0:
                scool_line = f"\n🧠 Cooldown aktiv ({remaining}s)"

    # Zeilen
    lines = [
        f"{color} {trade_info} | 💼 ${einsatz:.2f} | {lev_str}",
        f"PnL: ${pnl:.2f} | Laufzeit: {runtime_str} | ⏰ {uhrzeit} | 📅 {datum}",
        f"📉 ATR: ${atr:.2f} | 📈 EMA: {ema_trend} | {modus}",
        "",
        filter_line + scool_line,
        Style.RESET_ALL  # Damit Farbcodes zurückgesetzt werden (wenn im CMD)
    ]
    return "\n".join(lines)

def print_entry_status(position: dict, capital, app, leverage: int, settings: dict):
    print(get_entry_status_text(position, capital, app, leverage, settings))
