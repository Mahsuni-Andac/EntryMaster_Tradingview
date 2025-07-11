
"""Entry signal evaluation with adaptive logic and re-entry control."""

# Changelog
# - Introduced ``EntryDecision`` dataclass
# - Removed unused ``numpy`` import
# - Added type hints and module docstring

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EntryDecision:
    """Structured result of an entry evaluation."""

    entry_type: Optional[str]
    sl: Optional[float]
    adaptive: bool
    allow_reentry: bool
    long_signal: bool
    short_signal: bool

class EntryMasterEngine:
    """Evaluate entries and manage re-entry cooldowns."""

    def __init__(self, config: Dict[str, Any], mode: str = "live") -> None:
        self.config = config
        self.mode = mode  # "live" oder "sim"
        self.last_entry_type: Optional[str] = None
        self.last_sl_type: Optional[str] = None
        self.cooldown: int = 0
        self.active_reentry: bool = False

    def evaluate_entry(
        self, candle: Dict[str, float], context: Dict[str, Any]
    ) -> EntryDecision:
        """Return an entry decision for the provided *candle* and *context*."""

        open_, close, high, low = (
            candle["open"],
            candle["close"],
            candle["high"],
            candle["low"],
        )
        body = abs(close - open_)
        wick_top = high - max(open_, close)
        wick_bot = min(open_, close) - low
        candle_range = high - low

        # Fix: Edge-Case Division durch 0 sauber abfangen!
        if candle_range == 0:
            return EntryDecision(
                entry_type=None,
                sl=None,
                adaptive=True,
                allow_reentry=False,
                long_signal=False,
                short_signal=False,
            )

        wick_ratio_top = wick_top / candle_range
        wick_ratio_bot = wick_bot / candle_range

        # Adaptive Entry
        long_signal = (
            body / candle_range > 0.5 and
            wick_ratio_bot > 0.3 and  # Deutlicher Rejection-Wick unten
            context.get("momentum", 0) > 0 and
            close > context.get("ema", 0)
        )
        short_signal = (
            body / candle_range > 0.5 and
            wick_ratio_top > 0.3 and  # Deutlicher Rejection-Wick oben
            context.get("momentum", 0) < 0 and
            close < context.get("ema", 0)
        )

        # Breakout & Support-Bounce Detection (Optional Erweiterbar)
        breakout_long = False
        breakout_short = False
        if "history" in context and len(context["history"]) >= 5:
            breakout_long = close > max(c["high"] for c in context["history"][-5:])
            breakout_short = close < min(c["low"] for c in context["history"][-5:])

        # Adaptive SL
        sl = None
        if long_signal:
            sl = min(low, context["support"] if "support" in context else low)
        elif short_signal:
            sl = max(high, context["resistance"] if "resistance" in context else high)

        entry_type = None
        if long_signal or breakout_long:
            entry_type = "long"
        elif short_signal or breakout_short:
            entry_type = "short"

        # Smart Re-Entry bei Fehlausbruch (nur nach SL)
        allow_reentry = self.active_reentry and self.cooldown == 0

        return EntryDecision(
            entry_type=entry_type,
            sl=sl,
            adaptive=True,
            allow_reentry=allow_reentry,
            long_signal=long_signal,
            short_signal=short_signal,
        )

    def register_sl(self, sl_type: str = "default") -> None:
        """Register a stop-loss event and enable re-entry cooldown."""
        self.last_sl_type = sl_type
        self.active_reentry = True
        self.cooldown = self.config.get("reentry_cooldown", 3)

    def tick(self) -> None:
        """Advance the internal cooldown timer."""
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.cooldown == 0:
            self.active_reentry = False
