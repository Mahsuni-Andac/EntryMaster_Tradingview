# ADDED: asynchronous signal processing worker
"""Worker thread for strategy calculations."""

import threading
import queue
import logging
from typing import Callable, Any


class SignalWorker:
    """Process candle data on a separate thread."""

    def __init__(self, handler: Callable[[dict], Any], maxsize: int = 100) -> None:
        self.handler = handler
        self.queue: queue.Queue[dict] = queue.Queue(maxsize=maxsize)
        self._running = False
        self.thread: threading.Thread | None = None
        self.logger = logging.getLogger(__name__)

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self._running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self._running = False

    def is_alive(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def submit(self, candle: dict) -> None:
        try:
            self.queue.put_nowait(candle)
        except queue.Full:
            self.logger.warning("⚠️ Feed überlastet – Candles könnten verloren gehen")

    def _run(self) -> None:
        while self._running:
            try:
                candle = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                self.handler(candle)
            except Exception as exc:
                self.logger.error("SignalWorker Fehler: %s", exc)
