# global_state.py
#
# Changelog:
# - Added explicit types and reset helper

from __future__ import annotations

from typing import Optional, Dict

# 🌐 Globale Zustände für Entry-/Exit-Logik & UI-Komponenten
entry_time_global: Optional[float] = None
ema_trend_global: str = "⬆️"  # Standardwert setzen
atr_value_global: float = 42.7
position_global: Optional[Dict[str, float]] = None
last_feed_time: Optional[float] = None

def reset_global_state() -> None:
    """Reset shared global variables."""
    global entry_time_global, ema_trend_global, atr_value_global, position_global, last_feed_time
    entry_time_global = None
    ema_trend_global = "⬆️"  # Standardwert zurücksetzen
    atr_value_global = 42.7
    position_global = None
    last_feed_time = None
