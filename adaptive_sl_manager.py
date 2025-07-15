# adaptive_sl_manager.py

import numpy as np
import math

class AdaptiveSLManager:
    def __init__(self, atr_period=14):
        self.atr_period = atr_period

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


    def get_adaptive_sl_tp(self, direction, entry_price, candles, sl_multiplier=0.8, tp_multiplier=1.5):
        direction = direction.lower()
        if direction not in ("long", "short"):
            raise ValueError("Richtung muss 'long' oder 'short' sein.")

        atr = self.calculate_atr(candles)
        entry_price = float(entry_price)
        sl_multiplier = float(sl_multiplier)
        tp_multiplier = float(tp_multiplier)

        if direction == "long":
            sl = entry_price - atr * sl_multiplier
            tp = entry_price + atr * tp_multiplier
        else:
            sl = entry_price + atr * sl_multiplier
            tp = entry_price - atr * tp_multiplier

        return round(sl, 2), round(tp, 2)
