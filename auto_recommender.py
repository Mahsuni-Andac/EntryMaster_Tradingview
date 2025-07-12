"""Threaded helper that periodically adjusts GUI settings."""

from __future__ import annotations

import threading
import time
from typing import Optional


class AutoRecommender:
    """Apply dynamic filter recommendations while the bot is running."""

    def __init__(self, gui, interval: int = 10) -> None:
        self.gui = gui
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    def _run(self) -> None:
        while self._running:
            if (
                getattr(self.gui, "running", False)
                and hasattr(self.gui, "auto_apply_recommendations")
                and self.gui.auto_apply_recommendations.get()
            ):
                try:
                    self.gui.apply_recommendations()
                except Exception as exc:
                    if hasattr(self.gui, "log_event"):
                        self.gui.log_event(f"⚠️ Auto-Empfehlung Fehler: {exc}")
            time.sleep(self.interval)
