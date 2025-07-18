# adaptive_sl_manager.py

import numpy as np
import math

class AdaptiveSLManager:
    def __init__(self, atr_period=14, wick_lookback=7, atr_buffer=0.15):
        self.atr_period = atr_period
        self.wick_lookback = wick_lookback
        self.atr_buffer = atr_buffer

    def calculate_atr(self, candles):
        if len(candles) < self.atr_period + 1:
            raise ValueError(f"Mindestens {self.atr_period+1} Kerzen für ATR-Berechnung nötig.")
        trs = []
        for i in range(-self.atr_period, 0):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        atr = float(np.mean(trs))
        if atr is None or atr < 1e-5 or math.isnan(atr):
            raise ValueError("ATR zu klein oder ungültig")
        return atr

    def find_swing_low(self, candles):
        lows = [c["low"] for c in candles[-self.wick_lookback:]]
        return min(lows) if lows else None

    def find_swing_high(self, candles):
        highs = [c["high"] for c in candles[-self.wick_lookback:]]
        return max(highs) if highs else None

    def get_adaptive_sl_tp(self, direction, entry_price, candles, sl_multiplier=0.8, tp_multiplier=1.5):
        direction = direction.lower()
        if direction not in ("long", "short"):
            raise ValueError("Richtung muss 'long' oder 'short' sein.")

        atr = self.calculate_atr(candles)
        entry_price = float(entry_price)
        sl_multiplier = float(sl_multiplier)
        tp_multiplier = float(tp_multiplier)

        if direction == "long":
            swing_low = self.find_swing_low(candles)
            if swing_low is None:
                raise ValueError("Nicht genug Kerzen für swing_low.")
            sl = min(entry_price - atr * sl_multiplier, swing_low - atr * self.atr_buffer)
            tp = entry_price + atr * tp_multiplier
        else:
            swing_high = self.find_swing_high(candles)
            if swing_high is None:
                raise ValueError("Nicht genug Kerzen für swing_high.")
            sl = max(entry_price + atr * sl_multiplier, swing_high + atr * self.atr_buffer)
            tp = entry_price - atr * tp_multiplier

        return round(sl, 2), round(tp, 2)
