# smart_cooldown.py

import time

class SmartCooldownManager:
    def __init__(self):
        self.loss_count = 0
        self.last_loss_time = 0.0

    def should_trigger(self, pnl: float, duration_sec: int, signal_score: float, volume_ok: bool, candle_range: float, atr: float) -> tuple[bool, dict | None]:
        if pnl >= 0:
            self.loss_count = 0
            return False, None

        # Klassifiziere SL-Ursache
        sl_reason = self.classify_sl(candle_range, atr)

        # Triggerbedingungen
        fast_loss = duration_sec < 120
        weak_signal = signal_score < 0.55
        low_volume = not volume_ok
        small_range = candle_range < 0.8 * atr
        repeated = self.loss_count >= 2

        # Grunddaten
        reason_details = {
            "loss_count": self.loss_count,
            "sl_reason": sl_reason,
            "signal_score": signal_score,
            "fast_loss": fast_loss,
            "low_volume": low_volume,
            "small_range": small_range,
            "duration_sec": duration_sec,
            "trigger_type": ""
        }

        # Repeated loss
        if repeated:
            reason_details["trigger_type"] = "repeated"
            self._mark_loss()
            return True, reason_details

        # Mehrfach-Schwäche
        if fast_loss and weak_signal and low_volume:
            reason_details["trigger_type"] = "triple-weak"
            self._mark_loss()
            return True, reason_details

        # Rauschen + schwaches Signal
        if sl_reason == "noise" and weak_signal and small_range:
            reason_details["trigger_type"] = "noise-failure"
            self._mark_loss()
            return True, reason_details

        return False, None

    def classify_sl(self, candle_range: float, atr: float) -> str:
        return "noise" if candle_range < 0.5 * atr else "trend"

    def reset_losses(self):
        self.loss_count = 0

    def _mark_loss(self):
        self.loss_count += 1
        self.last_loss_time = time.time()

    def get_adaptive_duration(self) -> int:
        base = 180  # 3 Minuten
        extra = min(self.loss_count, 5) * 60
        return base + extra

    def get_remaining_cooldown(self) -> int:
        if self.last_loss_time == 0:
            return 0
        elapsed = time.time() - self.last_loss_time
        remaining = self.get_adaptive_duration() - elapsed
        return max(0, int(remaining))
