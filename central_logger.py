# central_logger.py
import logging
import sys
import time
from typing import List


class SafeStreamHandler(logging.StreamHandler):

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = self.format(record)
            fallback = msg.encode("ascii", "replace").decode("ascii") + " [ASCII-Fallback]"
            stream = self.stream
            stream.write(fallback + self.terminator)
            self.flush()


def setup_logging(level: int = logging.INFO, logfile: str = "bot.log") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
            SafeStreamHandler(sys.stdout),
        ],
    )


if not logging.getLogger().handlers:
    setup_logging()

_last_msg: str | None = None
_last_time: float = 0.0
_repeat: int = 0
_INTERVAL = 60.0


def log_messages(msg: str, level: int = logging.INFO) -> List[str]:
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
