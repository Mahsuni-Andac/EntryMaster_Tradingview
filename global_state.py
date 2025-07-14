# global_state.py

from __future__ import annotations

from typing import Optional, Dict

entry_time_global: Optional[float] = None
ema_trend_global: str = "⬆️"
atr_value_global: float | None = None
position_global: Optional[Dict[str, float]] = None
last_feed_time: Optional[float] = None
last_candle_ts: Optional[int] = None

def reset_global_state() -> None:
    """Reset all global trading state variables."""
    global entry_time_global, ema_trend_global, atr_value_global, position_global, last_feed_time, last_candle_ts
    entry_time_global = None
    ema_trend_global = "⬆️"
    atr_value_global = 42.7
    position_global = None
    last_feed_time = None
    last_candle_ts = None
