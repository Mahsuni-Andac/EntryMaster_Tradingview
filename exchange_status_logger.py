"""Utility to log exchange statuses from a credential dictionary.

This module provides functions to iterate over a ``creds`` dict and
safely log the status of every exchange.  Only entries that look like an
exchange (``name -> (bool, message)``) are considered.  Additional fields
such as ``active`` or ``live`` are ignored gracefully so that
``log_exchange_statuses`` never raises an exception due to malformed
entries.

Example
-------
>>> logging.basicConfig(level=logging.INFO, format="%(message)s")
>>> creds = {
...     "mexc": (True, "\u2705 Mexc API OK \u2013 Live-Marktdaten werden empfangen"),
...     "bitmex": (True, "\u2705 BitMEX API OK \u2013 Live-Marktdaten werden empfangen"),
...     "active": ["mexc", "bitmex"],
...     "live": True,
... }
>>> log_exchange_statuses(creds)
mexc -> \u2705 Mexc API OK \u2013 Live-Marktdaten werden empfangen
bitmex -> \u2705 BitMEX API OK \u2013 Live-Marktdaten werden empfangen
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, Tuple


@dataclass(frozen=True)
class ExchangeStatus:
    """Normalized representation of an exchange status."""

    is_ok: bool
    message: str


def iter_exchange_statuses(creds: Dict[str, Any]) -> Iterator[Tuple[str, ExchangeStatus]]:
    """Yield ``(name, ExchangeStatus)`` pairs for valid exchange entries.

    The function skips global or malformed items.  It never raises an
    exception when encountering unexpected values.
    """

    for name, value in creds.items():
        if name in {"active", "live"}:
            continue

        if isinstance(value, (tuple, list)) and len(value) >= 2:
            is_ok, message, *_ = value
            if isinstance(is_ok, bool) and isinstance(message, str):
                yield name, ExchangeStatus(is_ok, message)
            else:
                logging.debug("Invalid types for %s: %r", name, value)
        else:
            logging.debug("Skipping unknown key %s with value %r", name, value)


def log_exchange_statuses(creds: Dict[str, Any]) -> None:
    """Log the status of each exchange contained in ``creds``.

    Entries that do not match the expected structure are ignored.  The
    log level is :func:`logging.INFO` for healthy exchanges and
    :func:`logging.WARNING` otherwise.
    """

    logger = logging.getLogger(__name__)
    for name, status in iter_exchange_statuses(creds):
        level = logging.INFO if status.is_ok else logging.WARNING
        logger.log(level, "%s -> %s", name, status.message)


if __name__ == "__main__":  # pragma: no cover - manual run
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    example = {
        "mexc": (True, "\u2705 Mexc API OK \u2013 Live-Marktdaten werden empfangen"),
        "bitmex": (
            True,
            "\u2705 BitMEX API OK \u2013 Live-Marktdaten werden empfangen",
        ),
        "active": ["mexc", "bitmex"],
        "live": True,
    }
    log_exchange_statuses(example)
