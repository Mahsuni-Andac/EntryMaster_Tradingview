# exit_handler.py
"""Handle closing positions via BitMEX REST."""

from __future__ import annotations

import logging
from typing import Optional

import bitmex_interface as bm

logger = logging.getLogger(__name__)


def close_position() -> Optional[dict]:
    """Close any open BitMEX position."""
    try:
        return bm.close_position()
    except Exception as exc:
        logger.error("close_position failed: %s", exc)
        return None


def fetch_open_position() -> Optional[dict]:
    """Get current open position on BitMEX."""
    try:
        return bm.get_open_position()
    except Exception as exc:
        logger.error("fetch_open_position failed: %s", exc)
        return None


def close_partial_position(quantity: float) -> Optional[dict]:
    """Close part of the current position using a ReduceOnly market order."""
    try:
        position = bm.get_open_position()
        if not position or not position.get("currentQty"):
            logger.error("close_partial_position failed: no open position")
            return None
        side = "SELL" if position["currentQty"] > 0 else "BUY"
        return bm.place_order(side, quantity, reduce_only=True)
    except Exception as exc:
        logger.error("close_partial_position failed: %s", exc)
        return None
