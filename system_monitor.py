"""Real-time system monitoring with auto-pause/resume.

The monitor inspects the ``global_state.last_feed_time`` timestamp every
few seconds for the **active market only**.  Short interruptions are
tolerated (``timeout`` defaults to 10s).  If the timestamp becomes older
than ``timeout`` seconds, the bot is paused, an acoustic signal is emitted
and the GUI status switches to ``❌``.  As soon as a fresh tick updates the
timestamp the bot resumes and the status changes back to ``✅``.
"""

from __future__ import annotations

from datetime import datetime
import threading
import time
from typing import Optional

from config import SETTINGS
from credential_checker import check_all_credentials
from status_events import StatusDispatcher
import global_state

DISPLAY_NAMES = {
    "mexc": "MEXC",
    "dydx": "dYdX",
    "binance": "Binance",
    "bybit": "Bybit",
    "okx": "OKX",
    "bitmex": "BitMEX",
}


def _beep() -> None:
    """Trigger a simple beep sound in the console."""
    try:
        print("\a", end="", flush=True)
    except Exception:
        pass


class SystemMonitor:
    """Background watchdog for API and market data integrity."""

    def __init__(self, gui, interval: int = 2, timeout: int = 10) -> None:
        """Create monitor with *interval* seconds and feed ``timeout``.

        ``interval`` controls how often the APIs are polled.  If no candle
        update happens within ``timeout`` seconds (default ``10``) the bot will
        be paused automatically.
        """
        self.gui = gui
        self.interval = max(1, interval)
        self.timeout = timeout
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._feed_ok = True
        self._api_ok = True
        self._pause_reason: Optional[str] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if global_state.last_feed_time is None:
            global_state.last_feed_time = time.time()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    # ---- Internals -----------------------------------------------------
    def _log(self, msg: str) -> None:
        from central_logger import log_messages

        for line in log_messages(msg):
            stamp = datetime.now().strftime("[%H:%M:%S]")
            full = f"{stamp} {line}"
            if hasattr(self.gui, "log_event"):
                self.gui.log_event(full)
            else:
                print(full)

    def _run(self) -> None:
        while self._running:
            try:
                enabled = SETTINGS.get("enabled_exchanges") or []
                if not enabled:
                    time.sleep(self.interval)
                    continue
                creds = check_all_credentials(SETTINGS, enabled)
                if hasattr(self.gui, "update_exchange_status"):
                    for ex, (ok, _msg) in creds.items():
                        if ex in {"active", "live"}:
                            continue
                        disp = DISPLAY_NAMES.get(ex, ex)
                        self.gui.update_exchange_status(disp, ok)

                if creds.get("live"):
                    self._handle_api_up()
                else:
                    self._handle_api_down()
                    time.sleep(self.interval)
                    continue

                ts = global_state.last_feed_time
                if ts is None:
                    self._handle_feed_down("Keine Marktdaten empfangen")
                elif time.time() - ts > self.timeout:
                    self._handle_feed_down("Marktdaten aktualisieren sich nicht")
                else:
                    self._handle_feed_up()
            except Exception as exc:
                info = f"{type(exc).__name__}: {exc}"
                if 'creds' in locals():
                    info += f" | creds={creds!r}"
                self._log(f"Systemmonitor Fehler: {info}")
                self._handle_feed_down("API-Fehler – Antwort unvollständig")
            time.sleep(self.interval)

    # ---- State Handlers -------------------------------------------------
    def _handle_api_down(self) -> None:
        if self._api_ok:
            _beep()
            reason = "API nicht erreichbar"
            self._log(f"{reason} – Bot pausiert")
            if hasattr(self.gui, "update_api_status"):
                self.gui.update_api_status(False, reason)
            StatusDispatcher.dispatch("api", False, reason)
            if getattr(self.gui, "running", False):
                self.gui.running = False
                self._pause_reason = "api"
        self._api_ok = False

    def _handle_api_up(self) -> None:
        if not self._api_ok:
            if hasattr(self.gui, "update_api_status"):
                self.gui.update_api_status(True)
            StatusDispatcher.dispatch("api", True)
            if not getattr(self.gui, "running", False) and self._pause_reason == "api":
                self.gui.running = True
            self._pause_reason = None
        else:
            if hasattr(self.gui, "update_api_status"):
                self.gui.update_api_status(True)
            StatusDispatcher.dispatch("api", True)
        self._api_ok = True

    def _handle_feed_down(self, reason: str) -> None:
        if self._feed_ok:
            _beep()
            self._log(f"{reason} – Bot pausiert")
            if hasattr(self.gui, "update_feed_status"):
                self.gui.update_feed_status(False, reason)
            StatusDispatcher.dispatch("feed", False, reason)
            if getattr(self.gui, "running", False):
                self.gui.running = False
                self._pause_reason = "feed"
        self._feed_ok = False

    def _handle_feed_up(self) -> None:
        if not self._feed_ok:
            if hasattr(self.gui, "update_feed_status"):
                self.gui.update_feed_status(True)
            StatusDispatcher.dispatch("feed", True)
            if not getattr(self.gui, "running", False) and self._pause_reason == "feed":
                self.gui.running = True
            self._pause_reason = None
        else:
            if hasattr(self.gui, "update_feed_status"):
                self.gui.update_feed_status(True)
            StatusDispatcher.dispatch("feed", True)
        self._feed_ok = True
