import logging
import sys
import time
from typing import List


def setup_logging(level: int = logging.INFO, logfile: str = "bot.log") -> None:
    """Configure root logger with file and console output."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logfile),
            logging.StreamHandler(sys.stdout),
        ],
    )


if not logging.getLogger().handlers:
    setup_logging()

# Simple deduplicating logger
_last_msg: str | None = None
_last_time: float = 0.0
_repeat: int = 0
_INTERVAL = 60.0  # seconds


def log_messages(msg: str, level: int = logging.INFO) -> List[str]:
    """Return lines to log, applying deduplication."""
    global _last_msg, _last_time, _repeat
    now = time.time()
    out: List[str] = []
    if msg == _last_msg:
        if now - _last_time < _INTERVAL:
            _repeat += 1
            return out
        if _repeat:
            out.append(f"{msg} ({_repeat}x wiederholt)")
        else:
            out.append(msg)
        _last_time = now
        _repeat = 0
    else:
        if _last_msg is not None and _repeat:
            out.append(f"{_last_msg} ({_repeat}x wiederholt)")
        out.append(msg)
        _last_msg = msg
        _last_time = now
        _repeat = 0
    for line in out:
        logging.log(level, line)
    return out
