# exit_handler.py
"""Handle closing positions via BitMEX REST."""

from typing import Optional
import bitmex_interface as bm
from utils import retry_on_failure

def close_position() -> Optional[dict]:
    """Close any open BitMEX position."""
    return bm.close_position()

@retry_on_failure(retries=3)
def close_partial_position(volume: float, order_type: str = "Market") -> Optional[dict]:
    """
    Closes part of the current position by specified volume.

    Args:
        volume (float): Contract size to close.
    """
    if volume <= 0:
        return None

    position = bm.get_open_position()
    if not position:
        return None

    side = "Sell" if position["currentQty"] > 0 else "Buy"
    return bm.place_order(side, abs(volume), reduce_only=True, order_type=order_type)

