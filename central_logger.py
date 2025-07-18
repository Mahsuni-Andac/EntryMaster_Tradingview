# central_logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler
import time
from typing import List

class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = self.format(record)
            fallback = msg.encode("utf-8", "replace").decode("utf-8")
            stream = self.stream
            stream.write(fallback + self.terminator)
            self.flush()
        except ValueError:
            pass  # detached buffer Error fix

def setup_logging(level: int = logging.INFO, logfile: str = "bot.log") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            RotatingFileHandler(logfile, maxBytes=1_000_000, backupCount=3, encoding='utf-8'),
            SafeStreamHandler(sys.__stdout__)  # sicheres Original-stdout
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

def log_triangle_signal(signal_type: str, price: float) -> str:
    from datetime import datetime
    stamp = datetime.now().strftime("%H:%M:%S")
    if signal_type == "long":
        msg = f"{stamp} GRÜN Dreieck (LONG) erkannt @ {price:.2f}"
    elif signal_type == "short":
        msg = f"{stamp} ROT Dreieck (SHORT) erkannt @ {price:.2f}"
    else:
        msg = f"{stamp} Unbekanntes Signal"
    logging.info(msg)
    return msg
