# cooldown_manager.py

from datetime import datetime, timedelta

class CooldownManager:
    def __init__(self, cooldown_minutes: int = 3, debug: bool = False):
        self.last_sl_time: datetime | None = None
        self.cooldown_period = timedelta(minutes=cooldown_minutes)
        self.debug = debug

    def register_sl(self, time_of_sl: float):
        self.last_sl_time = datetime.fromtimestamp(time_of_sl)
        if self.debug:
            end_time = self.last_sl_time + self.cooldown_period
            print(f"🔴 Cooldown aktiviert bis: {end_time.strftime('%H:%M:%S')}")

    def in_cooldown(self, current_time: float) -> bool:
        if not self.last_sl_time:
            return False
        now = datetime.fromtimestamp(current_time)
        active = now < self.last_sl_time + self.cooldown_period
        if self.debug:
            remaining = self.get_remaining_seconds(current_time)
            print(f"⏱️ Cooldown aktiv: {remaining}s verbleibend" if active else "🟢 Kein Cooldown")
        return active

    def get_remaining_seconds(self, current_time: float) -> int:
        if not self.last_sl_time:
            return 0
        remaining = (self.last_sl_time + self.cooldown_period) - datetime.fromtimestamp(current_time)
        return max(0, int(remaining.total_seconds()))

    def reset(self):
        self.last_sl_time = None
        if self.debug:
            print("🔄 Cooldown zurückgesetzt")

