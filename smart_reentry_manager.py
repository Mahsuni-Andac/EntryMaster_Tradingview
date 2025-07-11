# smart_reentry_manager.py
import time

class SmartReEntryManager:
    def __init__(self, cooldown_sec=60):
        self.last_reentry_time = 0
        self.last_direction = None
        self.last_exit_reason = ""
        self.fakeout_detected = False

    def should_reenter(self, last_position, current_candle, signal, cooldown_active, atr):
        """
        Prüft, ob ein Re-Entry sinnvoll ist:
        - letzter Trade SL nahe Support/Wick/Fakeout
        - aktuelle Candle zeigt schnelle Umkehr, starker Wick
        - Kein aktiver Re-Entry in Cooldown
        """
        now = time.time()
        if cooldown_active or (now - self.last_reentry_time) < 60:
            return False

        if not last_position or not last_position.get("exit_reason"):
            return False

        # Nur nach SL-Exit
        if last_position["exit_reason"] != "STOP-LOSS":
            return False

        # Re-Entry nur wenn Richtung beibehalten, Signal und schnelle Umkehr (Fakeout)
        direction = last_position["side"].lower()
        if direction != signal:
            return False

        # Wick-Detection: SL lag nahe letztem Support/Resistance, und Candle zeigt starken Rejection Wick
        close = current_candle["close"]
        high = current_candle["high"]
        low = current_candle["low"]
        entry = last_position["entry_price"]

        if direction == "long":
            # Fakeout Down: tiefer Wick, starker Rebound, SL-Auslösung direkt unter Support
            wick_len = (close - low)
            wick_ratio = wick_len / (high - low + 1e-9)
            sl_dist = abs(last_position["stop_loss"] - low)
            # Bedingungen: starker unterer Wick und SL-Auslösung in der Nähe + Close erholt
            if wick_ratio > 0.5 and sl_dist < 0.25 * atr and close > entry:
                self.last_reentry_time = now
                self.last_direction = direction
                self.last_exit_reason = "fakeout"
                self.fakeout_detected = True
                return True

        else:
            # Fakeout Up: oberer Wick, starker Abverkauf, SL nahe Resistance
            wick_len = (high - close)
            wick_ratio = wick_len / (high - low + 1e-9)
            sl_dist = abs(last_position["stop_loss"] - high)
            if wick_ratio > 0.5 and sl_dist < 0.25 * atr and close < entry:
                self.last_reentry_time = now
                self.last_direction = direction
                self.last_exit_reason = "fakeout"
                self.fakeout_detected = True
                return True

        return False
