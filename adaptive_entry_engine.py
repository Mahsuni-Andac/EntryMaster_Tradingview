# adaptive_entry_engine.py
import numpy as np

class AdaptiveEntryEngine:
    def __init__(self, min_body_ratio=0.5, min_momentum=1.2, wick_reject_ratio=0.3, reentry_cooldown=3):
        self.min_body_ratio = min_body_ratio
        self.min_momentum = min_momentum
        self.wick_reject_ratio = wick_reject_ratio
        self.last_sl_time = None
        self.reentry_cooldown = reentry_cooldown

    def detect_entry(self, candles, ctx):
        """
        candles: List[dict] (mind. 2, ideal 10+), aktuelle Candle = candles[-1]
        ctx: Kontext, z. B. Trend, EMA, ATR etc.
        Rückgabe: {"signal": "long"/"short"/None, "reason": ...}
        """
        if len(candles) < 2:
            return None

        now = ctx.get("now", 0)
        # Re-Entry-Cooldown-Logik zuerst!
        if self.last_sl_time is not None and (now - self.last_sl_time) < self.reentry_cooldown:
            return None

        c = candles[-1]
        prev = candles[-2]

        open_, close, high, low = c["open"], c["close"], c["high"], c["low"]
        prev_close = prev["close"]
        body = abs(close - open_)
        candle_range = high - low

        # Adaptive Body-Ratio-Check
        if candle_range == 0 or (body / candle_range) < self.min_body_ratio:
            return None

        # Momentum: Distance zur vorigen Range
        prev_range = prev["high"] - prev["low"] + 1e-8
        momentum = abs(close - prev_close) / prev_range
        if momentum < self.min_momentum:
            return None

        # Wick-Rejection Detection
        lower_wick = min(open_, close) - low
        upper_wick = high - max(open_, close)
        if close > open_:
            # Bullish
            if lower_wick / candle_range < self.wick_reject_ratio:
                return None
        else:
            # Bearish
            if upper_wick / candle_range < self.wick_reject_ratio:
                return None

        # Trend-Check (z. B. EMA-Align)
        trend = ctx.get("trend", "neutral")
        if close > open_ and trend == "up":
            return {"signal": "long", "reason": "bull-structure + trend"}
        elif close < open_ and trend == "down":
            return {"signal": "short", "reason": "bear-structure + trend"}

        # Marktrauschen vermeiden
        if ctx.get("avoid_chop", False):
            if ctx.get("chop_score", 0) > 0.5:
                return None

        return None

    def register_stop_loss(self, now):
        self.last_sl_time = now
