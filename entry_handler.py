# entry_handler.py
"""Handle opening positions via BitMEX REST."""

from __future__ import annotations

import logging
from typing import Optional

import bitmex_interface as bm

logger = logging.getLogger(__name__)


def open_position(side: str, quantity: float, reduce_only: bool = False) -> Optional[dict]:
    """Open a position on BitMEX."""
    try:
        return bm.place_order(side, quantity, reduce_only=reduce_only)
    except Exception as exc:
        logger.error("open_position failed: %s", exc)
        return None
