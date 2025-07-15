# cooldown_manager.py

from datetime import datetime, timedelta
import time

class CooldownManager:
    def __init__(self, cooldown_minutes: int = 3, debug: bool = False):
        self.last_sl_time: datetime | None = None
        self.cooldown_period = timedelta(minutes=cooldown_minutes)
        self.cooldown_duration = cooldown_minutes * 60
        self.cooldown_until = 0.0
        self.debug = debug

    def register_sl(self, time_of_sl: float):
        self.last_sl_time = datetime.fromtimestamp(time_of_sl)
        self.cooldown_until = time_of_sl + self.cooldown_duration
        if self.debug:
            end_time = datetime.fromtimestamp(self.cooldown_until)
            print(f"🔴 Cooldown aktiviert bis: {end_time.strftime('%H:%M:%S')}")

    def in_cooldown(self, current_time: float) -> bool:
        if not self.last_sl_time:
            return False
        active = current_time < self.cooldown_until
        if self.debug:
            remaining = self.get_remaining_seconds(current_time)
            print(f"⏱️ Cooldown aktiv: {remaining}s verbleibend" if active else "🟢 Kein Cooldown")
        return active

    def get_remaining_seconds(self, current_time: float) -> int:
        if not self.last_sl_time:
            return 0
        remaining = self.cooldown_until - current_time
        return max(0, int(remaining))

    def reset(self):
        self.last_sl_time = None
        self.cooldown_until = 0.0
        if self.debug:
            print("🔄 Cooldown zurückgesetzt")

    # ------------------------------------------------------------------
    # simplified interface used by GUI

    def set_cooldown(self, minutes: int) -> None:
        self.cooldown_duration = minutes * 60
        self.cooldown_period = timedelta(minutes=minutes)

    def activate(self) -> None:
        now = time.time()
        self.cooldown_until = now + self.cooldown_duration
        self.last_sl_time = datetime.fromtimestamp(now)
        if self.debug:
            end_time = datetime.fromtimestamp(self.cooldown_until)
            print(f"🔴 Cooldown aktiviert bis: {end_time.strftime('%H:%M:%S')}")

    def is_active(self) -> bool:
        return time.time() < self.cooldown_until

