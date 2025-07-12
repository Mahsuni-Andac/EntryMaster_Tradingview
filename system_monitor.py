"""Real-time system monitoring with auto-pause/resume.

This watchdog checks exchange connectivity and incoming market data every
few seconds for the **active market only**.  Short interruptions are tolerated
(``timeout`` defaults to 10s).  If no fresh candle is received within this
period the bot is paused, an acoustic signal is emitted and the GUI status
switches to ``❌``.  As soon as a new candle arrives the bot resumes and the
status changes back to ``✅``.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional

from config import SETTINGS
from credential_checker import check_all_credentials
from data_provider import fetch_latest_candle


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
        self._last_candle_ts: Optional[int] = None
        self._last_update = time.time()
        self._feed_ok = True
        self._api_ok = True
        self._pause_reason: Optional[str] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if hasattr(self.gui, "update_api_status"):
            self.gui.update_api_status(True)
        if hasattr(self.gui, "update_feed_status"):
            self.gui.update_feed_status(True)
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
        stamp = datetime.now().strftime("[%H:%M:%S]")
        full = f"{stamp} {msg}"
        if hasattr(self.gui, "log_event"):
            self.gui.log_event(full)
        else:
            print(full)

    def _run(self) -> None:
        while self._running:
            try:
                creds = check_all_credentials(SETTINGS)
                if creds.get("live"):
                    self._handle_api_up()
                else:
                    self._handle_api_down()
                    time.sleep(self.interval)
                    continue

                candle = fetch_latest_candle(
                    SETTINGS.get("symbol", "BTCUSDT"),
                    SETTINGS.get("interval", "1m"),
                )
                if not candle:
                    self._handle_feed_down("Keine Marktdaten empfangen")
                    time.sleep(self.interval)
                    continue

                ts = candle.get("timestamp")
                if ts != self._last_candle_ts:
                    self._last_candle_ts = ts
                    self._last_update = time.time()
                    self._handle_feed_up()
                elif time.time() - self._last_update > self.timeout:
                    self._handle_feed_down("Marktdaten aktualisieren sich nicht")
                else:
                    self._handle_feed_up()
            except Exception as exc:
                self._handle_feed_down(f"Systemmonitor Fehler: {exc}")
            time.sleep(self.interval)

    # ---- State Handlers -------------------------------------------------
    def _handle_api_down(self) -> None:
        if self._api_ok:
            _beep()
            self._log("API nicht erreichbar – Bot pausiert")
            if hasattr(self.gui, "update_api_status"):
                self.gui.update_api_status(False)
            if getattr(self.gui, "running", False):
                self.gui.running = False
                self._pause_reason = "api"
        self._api_ok = False

    def _handle_api_up(self) -> None:
        if not self._api_ok:
            self._log("✅ API wieder erreichbar – Bot läuft weiter")
            if hasattr(self.gui, "update_api_status"):
                self.gui.update_api_status(True)
            if not getattr(self.gui, "running", False) and self._pause_reason == "api":
                self.gui.running = True
            self._pause_reason = None
        else:
            if hasattr(self.gui, "update_api_status"):
                self.gui.update_api_status(True)
        self._api_ok = True

    def _handle_feed_down(self, reason: str) -> None:
        if self._feed_ok:
            _beep()
            self._log(f"{reason} – Bot pausiert")
            if hasattr(self.gui, "update_feed_status"):
                self.gui.update_feed_status(False)
            if getattr(self.gui, "running", False):
                self.gui.running = False
                self._pause_reason = "feed"
        self._feed_ok = False

    def _handle_feed_up(self) -> None:
        if not self._feed_ok:
            self._log("✅ Marktdaten-Feed wieder aktiv – Bot läuft weiter")
            if hasattr(self.gui, "update_feed_status"):
                self.gui.update_feed_status(True)
            if not getattr(self.gui, "running", False) and self._pause_reason == "feed":
                self.gui.running = True
            self._pause_reason = None
        else:
            if hasattr(self.gui, "update_feed_status"):
                self.gui.update_feed_status(True)
        self._feed_ok = True
