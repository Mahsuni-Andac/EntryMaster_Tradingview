# bitmex_interface.py
"""Wrapper module exposing BitMEX REST calls via :class:`BitmexClient`."""

from __future__ import annotations

import logging
from typing import Optional

from bitmex_client import BitmexClient

logger = logging.getLogger(__name__)

# Instantiate a single client using credentials from environment variables
client = BitmexClient()


def place_order(side: str, quantity: float, reduce_only: bool = False,
                order_type: str = "Market") -> Optional[dict]:
    """Place an order on BitMEX."""
    try:
        return client.place_order(
            side, quantity, reduce_only=reduce_only, order_type=order_type
        )
    except Exception as exc:
        logger.error("❌ BitMEX-Order fehlgeschlagen: %s", exc)
        return None


def close_position() -> Optional[dict]:
    """Close any open position using a market order."""
    try:
        return client.close_position()
    except Exception as exc:
        logger.error("close_position failed: %s", exc)
        return None


def get_open_position() -> Optional[dict]:
    """Return current open position for XBTUSD if any."""
    try:
        return client.get_open_position()
    except Exception as exc:
        logger.error("get_open_position failed: %s", exc)
        return None


def set_credentials(key: str, secret: str) -> None:
    """Set API credentials for subsequent requests."""
    client.api_key = key
    client.api_secret = secret


def check_credentials() -> bool:
    """Verify that the current credentials are valid."""
    try:
        client.get_open_position()
        return True
    except Exception as exc:
        logger.error("check_credentials failed: %s", exc)
        return False

