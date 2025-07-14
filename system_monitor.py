# system_monitor.py

from __future__ import annotations

from datetime import datetime
import threading
import time
from typing import Optional

from status_events import StatusDispatcher
import logging
import global_state


def _beep() -> None:
    try:
        print("\a", end="", flush=True)
    except Exception:
        pass


class SystemMonitor:

    def __init__(self, gui, interval: int = 2, timeout: int = 10) -> None:
        self.gui = gui
        self.interval = max(1, interval)
        self.timeout = timeout
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._feed_ok = True
        self._pause_reason: Optional[str] = None
        self._last_checked_ts: Optional[float] = None

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

    def _log(self, msg: str) -> None:
        from central_logger import log_messages

        for line in log_messages(msg):
            stamp = datetime.now().strftime("[%H:%M:%S]")
            full = f"{stamp} {line}"
            if hasattr(self.gui, "log_event"):
                self.gui.log_event(full)
            else:
                logging.getLogger(__name__).info(full)

    def _run(self) -> None:
        while self._running:
            try:
                ts = global_state.last_feed_time
                if ts == self._last_checked_ts:
                    time.sleep(self.interval)
                    continue
                self._last_checked_ts = ts
                if ts is None:
                    self._handle_feed_down("Keine Marktdaten empfangen")
                elif time.time() - ts > 30:
                    self._handle_feed_down("Marktdaten aktualisieren sich nicht")
                else:
                    self._handle_feed_up()
            except Exception as exc:
                info = f"{type(exc).__name__}: {exc}"
                logging.debug("Systemmonitor exception: %s", info)
                self._handle_feed_down("API-Fehler – Antwort unvollständig", log=False)
            time.sleep(self.interval)


    def _handle_feed_down(self, reason: str, *, log: bool = True) -> None:
        if self._feed_ok:
            _beep()
            if log:
                self._log(f"{reason} – Bot pausiert")
            if hasattr(self.gui, "update_feed_status"):
                self.gui.update_feed_status(False, reason)
            StatusDispatcher.dispatch("feed", False, reason)
            if getattr(self.gui, "running", False):
                self.gui.running = False
                self._pause_reason = "feed"
        self._feed_ok = False

    def _handle_feed_up(self) -> None:
        if not self._feed_ok and not getattr(self.gui, "running", False) and self._pause_reason == "feed":
            self.gui.running = True
        self._pause_reason = None
        if hasattr(self.gui, "update_feed_status"):
            self.gui.update_feed_status(True)
        StatusDispatcher.dispatch("feed", True)
        self._feed_ok = True
