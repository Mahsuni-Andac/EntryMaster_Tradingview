"""Real-time system monitoring and auto-pause utilities."""

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

    def __init__(self, gui, interval: int = 15) -> None:
        self.gui = gui
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_candle_ts: Optional[int] = None

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
            if not getattr(self.gui, "running", False):
                time.sleep(1)
                continue
            try:
                creds = check_all_credentials(SETTINGS)
                if not creds.get("live"):
                    _beep()
                    self._log("API nicht erreichbar – Bot pausiert")
                    self.gui.running = False
                    continue

                candle = fetch_latest_candle(SETTINGS.get("symbol", "BTCUSDT"), SETTINGS.get("interval", "1m"))
                if not candle:
                    _beep()
                    self._log("Keine Marktdaten empfangen – Bot pausiert")
                    self.gui.running = False
                    continue
                ts = candle.get("timestamp")
                if ts == self._last_candle_ts:
                    _beep()
                    self._log("Marktdaten aktualisieren sich nicht – Bot pausiert")
                    self.gui.running = False
                    continue
                self._last_candle_ts = ts
            except Exception as exc:
                _beep()
                self._log(f"Systemmonitor Fehler: {exc}")
                self.gui.running = False
            time.sleep(self.interval)
