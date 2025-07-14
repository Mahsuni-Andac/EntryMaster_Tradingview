# session_filter.py

from datetime import datetime, timedelta
from typing import Tuple, Dict, List

_GLOBAL_FILTER: "SessionFilter" | None = None

class SessionFilter:
    def __init__(
        self,
        allowed_sessions: Tuple[str, ...] = ("london", "new_york"),
        use_utc: bool = True,
        debug: bool = False,
    ) -> None:
        self.allowed_sessions = allowed_sessions
        self.use_utc = use_utc
        self.debug = debug
        self.session_times: Dict[str, Tuple[int, int]] = {
            "london": (6, 14),
            "new_york": (13, 21),
            "asia": (21, 6),
        }

    def configure(
        self,
        allowed_sessions: Tuple[str, ...] | None = None,
        use_utc: bool | None = None,
        debug: bool | None = None,
    ) -> None:
        """Update filter settings dynamically."""
        if allowed_sessions is not None:
            self.allowed_sessions = allowed_sessions
        if use_utc is not None:
            self.use_utc = use_utc
        if debug is not None:
            self.debug = debug

    def get_current_hour(self) -> int:
        now = datetime.utcnow()
        if not self.use_utc:
            now += timedelta(hours=2)
        return now.hour

    def get_current_session(self) -> str:
        hour = self.get_current_hour()
        for name, (start, end) in self.session_times.items():
            if start < end:
                if start <= hour < end:
                    return name
            else:
                if hour >= start or hour < end:
                    return name
        return "unknown"

    def is_allowed(self) -> bool:
        session = self.get_current_session()
        allowed = session in self.allowed_sessions
        if self.debug:
            print(f"🕒 Aktuelle Session: {session} | Erlaubt: {allowed}")
        return allowed

    def get_status(self) -> Dict[str, str | int | bool]:
        session = self.get_current_session()
        return {
            "current": session,
            "allowed": session in self.allowed_sessions,
            "hour": self.get_current_hour(),
            "mode": "UTC" if self.use_utc else "Local (CEST)"
        }


def get_global_filter(config: Dict[str, List[str] | bool] | None = None) -> SessionFilter:
    """Return a shared SessionFilter instance, applying ``config`` if given."""
    global _GLOBAL_FILTER
    if _GLOBAL_FILTER is None:
        _GLOBAL_FILTER = SessionFilter()
    if config is not None:
        allowed = config.get("allowed")
        allowed_sessions = tuple(allowed) if isinstance(allowed, list) else None
        _GLOBAL_FILTER.configure(
            allowed_sessions=allowed_sessions,
            use_utc=config.get("use_utc"),
            debug=config.get("debug"),
        )
    return _GLOBAL_FILTER
