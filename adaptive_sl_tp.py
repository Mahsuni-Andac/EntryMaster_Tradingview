# adaptive_sl_tp.py
import numpy as np

class AdaptiveSLTP:
    def __init__(self, sl_mode="auto", rr_ratio=2.0, atr_mult=0.7, wick_buffer=0.12):
        self.sl_mode = sl_mode        # "auto", "atr", "wick", "support"
        self.rr_ratio = rr_ratio      # Risk-Reward Verhältnis
        self.atr_mult = atr_mult
        self.wick_buffer = wick_buffer

    def calc_sl_tp(self, direction, entry, candle, ctx):
        """
        direction: "long" / "short"
        entry: Entry-Preis
        candle: dict mit OHLC
        ctx: dict mit context z. B. ATR, Support/Resist
        """
        high, low = candle["high"], candle["low"]
        atr = ctx.get("atr", 20)
        support = ctx.get("support", low)
        resistance = ctx.get("resistance", high)

        if direction == "long":
            wick_sl = low - (high - low) * self.wick_buffer
            atr_sl = entry - atr * self.atr_mult
            support_sl = support
            if self.sl_mode == "wick":
                sl = wick_sl
            elif self.sl_mode == "support":
                sl = support_sl
            elif self.sl_mode == "atr":
                sl = atr_sl
            else: # auto
                sl = max(wick_sl, support_sl, atr_sl)
            tp = entry + (entry - sl) * self.rr_ratio
        else:
            wick_sl = high + (high - low) * self.wick_buffer
            atr_sl = entry + atr * self.atr_mult
            resist_sl = resistance
            if self.sl_mode == "wick":
                sl = wick_sl
            elif self.sl_mode == "support":
                sl = resist_sl
            elif self.sl_mode == "atr":
                sl = atr_sl
            else: # auto
                sl = min(wick_sl, resist_sl, atr_sl)
            tp = entry - (sl - entry) * self.rr_ratio

        # Immer runden
        sl = round(sl, 2)
        tp = round(tp, 2)
        return sl, tp

    def smart_reentry_allowed(self, prev_sl_time, now, cooldown=3):
        """
        Gibt True zurück, wenn nach SL ein erneuter Entry erlaubt ist (nach x Candles)
        """
        if prev_sl_time is None:
            return True
        return (now - prev_sl_time) >= cooldown

