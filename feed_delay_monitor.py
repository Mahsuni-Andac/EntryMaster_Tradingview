# ADDED: monitor feed delay to detect lag
"""Simple timer-based feed delay monitor."""

import threading
import time
import logging
import global_state


def start(interval: int) -> None:
    """Start monitoring feed delays."""
    def _run():
        while True:
            last = global_state.last_feed_time
            if last and time.time() - last > interval:
                logging.warning(
                    "⚠️ Feed überlastet – Verzögerung %.1fs", time.time() - last
                )
            time.sleep(interval // 2)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
