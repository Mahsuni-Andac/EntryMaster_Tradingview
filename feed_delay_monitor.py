# ADDED: monitor feed delay to detect lag
"""Simple timer-based feed delay monitor."""

import threading
import time
import logging
import global_state
from queue import Queue
from status_events import StatusDispatcher


def start(interval: int, queue_obj: Queue | None = None) -> None:
    """Start monitoring feed delays."""
    def _run():
        while True:
            last = global_state.last_feed_time
            if last and time.time() - last > interval:
                logging.warning(
                    "⚠️ Feed überlastet – Verzögerung %.1fs", time.time() - last
                )
            if queue_obj is not None and queue_obj.qsize() > 10:
                logging.warning("⚠️ Feed-Stau: Queue > 10")
                StatusDispatcher.dispatch("feed", False, "Queue>10")
            time.sleep(interval // 2)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
