# exit_handler.py
"""Handle closing positions via BitMEX REST."""

from typing import Optional
from bitmex_client import BitmexClient

bm = BitmexClient()

def close_position() -> Optional[dict]:
    """Close any open BitMEX position."""
    return bm.close_position()

def close_partial_position(volume: float) -> Optional[dict]:
    """
    Closes part of the current position by specified volume.

    Args:
        volume (float): Contract size to close.
    """
    if volume <= 0:
        return None

    position = bm.get_position()
    if not position:
        return None

    side = "Sell" if position["currentQty"] > 0 else "Buy"
    response = bm.place_order(
        symbol="XBTUSD",
        side=side,
        orderQty=abs(volume),
        ordType="Market",
        reduceOnly=True
    )
    return response

