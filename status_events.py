from typing import Callable, Dict, List, Optional

class StatusDispatcher:
    """Simple event dispatcher for API/feed status changes."""

    _subs: Dict[str, List[Callable[[bool, Optional[str]], None]]] = {
        "api": [],
        "feed": [],
    }

    @classmethod
    def subscribe(cls, event: str, func: Callable[[bool, Optional[str]], None]) -> None:
        cls._subs.setdefault(event, []).append(func)

    @classmethod
    def on_api_status(cls, func: Callable[[bool, Optional[str]], None]) -> None:
        cls.subscribe("api", func)

    @classmethod
    def on_feed_status(cls, func: Callable[[bool, Optional[str]], None]) -> None:
        cls.subscribe("feed", func)

    @classmethod
    def dispatch(cls, event: str, ok: bool, reason: Optional[str] = None) -> None:
        for cb in cls._subs.get(event, []):
            try:
                cb(ok, reason)
            except Exception:
                pass
