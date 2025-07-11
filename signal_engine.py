# signal_engine.py

import numpy as np
from config import SETTINGS
from entry_score_engine import calculate_entry_score

class SignalEngine:
    def __init__(self, threshold=0.6):
        self.threshold = threshold
        self.candle_history = []
        self.close_history = []
        self.rsi_period = 14

    def evaluate(self, candle, settings=None):
        close = candle.get("close")
        high = candle.get("high")
        low = candle.get("low")
        open_ = candle.get("open")
        volume = candle.get("volume", 0)

        if not all([open_, high, low, close]):
            return None

        self.candle_history.append(candle)
        self.close_history.append(close)

        if len(self.candle_history) > 100:
            self.candle_history.pop(0)
        if len(self.close_history) > 100:
            self.close_history.pop(0)
        if len(self.close_history) < self.rsi_period + 1:
            return None

        # 📉 RSI & EMA
        rsi = self._calculate_rsi(self.close_history[-(self.rsi_period + 1):])
        ema = settings.get("ema_value", 0)
        ema_ok = close > ema if settings.get("use_ema_filter") else True
        rsi_ok = 40 < rsi < 70 if settings.get("use_rsi_filter") else True

        if settings:
            settings["last_rsi_allowed"] = rsi_ok
            settings["last_ema_allowed"] = ema_ok

        if not rsi_ok:
            if settings.get("log_event"): settings["log_event"](f"❌ RSI außerhalb Zielbereich ({rsi:.1f})")
            return None
        if not ema_ok:
            if settings.get("log_event"): settings["log_event"]("❌ EMA-Trend spricht gegen Entry")
            return None

        # 🕯️ Doji-Check
        body = abs(close - open_)
        candle_range = high - low
        if candle_range == 0 or body / candle_range < 0.2:
            if settings: settings["last_doji_allowed"] = False
            return None
        if len(self.candle_history) >= 2:
            prev = self.candle_history[-2]
            if high <= prev["high"] and low >= prev["low"]:
                if settings: settings["last_doji_allowed"] = False
                return None

        # 🧠 Indikatorprüfung
        prev = self.candle_history[-2]
        indicators = {
            "rsi": rsi,
            "volume_spike": volume > np.mean([c["volume"] for c in self.candle_history[-10:]]) * 1.5,
            "engulfing": (
                "bullish" if close > open_ and open_ < prev["close"] and close > prev["open"]
                else "bearish" if close < open_ and open_ > prev["close"] and close < prev["open"]
                else None
            ),
            "breakout": close > max(c["high"] for c in self.candle_history[-5:]) or
                        close < min(c["low"] for c in self.candle_history[-5:])
        }

        # 🎯 Score-Berechnung
        score, score_details = calculate_entry_score(candle, indicators, SETTINGS["score_config"])
        if settings:
            settings["last_score"] = score
            settings["last_score_details"] = score_details

        # 📡 Signalentscheidung
        signal_type = None
        if close > open_ and body / candle_range > 0.5 and indicators["engulfing"] == "bullish" and score >= self.threshold:
            signal_type = "long"
        elif close < open_ and body / candle_range > 0.5 and indicators["engulfing"] == "bearish" and score >= self.threshold:
            signal_type = "short"

        if signal_type:
            symbol = ("⤴️" if signal_type == "long" else "⤵️")
            if score > 0.8: symbol += "🤑"
            if indicators["breakout"] or indicators["volume_spike"]: symbol += "🚀"
            return {
                "signal": signal_type,
                "symbol": symbol,
                "score": score,
                "details": score_details,
                "rsi": rsi
            }

        return None

    def _calculate_rsi(self, closes):
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            (gains if diff > 0 else losses).append(abs(diff))
        avg_gain = sum(gains) / self.rsi_period
        avg_loss = sum(losses) / self.rsi_period or 0.000001
        rs = avg_gain / avg_loss
        return max(0, min(100, 100 - (100 / (1 + rs))))
