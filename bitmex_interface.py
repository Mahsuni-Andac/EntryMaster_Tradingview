# bitmex_interface.py
"""Simple BitMEX REST interface for order execution."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.bitmex.com"
API_KEY = os.getenv("BITMEX_API_KEY")
API_SECRET = os.getenv("BITMEX_API_SECRET")
SYMBOL = "XBTUSD"


def _make_headers(verb: str, path: str, data: str = "") -> dict:
    if not API_KEY or not API_SECRET:
        raise ValueError("API credentials not set")
    expires = str(int(time.time()) + 5)
    message = verb + path + expires + data
    signature = hmac.new(
        API_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return {
        "api-expires": expires,
        "api-key": API_KEY,
        "api-signature": signature,
        "content-type": "application/json",
    }


def place_order(side: str, quantity: float, reduce_only: bool = False) -> Optional[dict]:
    """Place a market order on BitMEX."""
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")
    path = "/api/v1/order"
    order = {"symbol": SYMBOL, "side": side.title(), "orderQty": quantity, "ordType": "Market"}
    if reduce_only:
        order["execInst"] = "ReduceOnly"
    data = json.dumps(order)
    headers = _make_headers("POST", path, data)
    url = BASE_URL + path
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("place_order failed: %s", exc)
        return None


def close_position() -> Optional[dict]:
    """Close any open position using a market order."""
    path = "/api/v1/order"
    data = json.dumps({"symbol": SYMBOL, "execInst": "Close", "ordType": "Market"})
    headers = _make_headers("POST", path, data)
    url = BASE_URL + path
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("close_position failed: %s", exc)
        return None


def get_open_position() -> Optional[dict]:
    """Return current open position for XBTUSD if any."""
    path = "/api/v1/position"
    params = {"filter": json.dumps({"symbol": SYMBOL}), "count": 1}
    query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    headers = _make_headers("GET", path + query)
    url = BASE_URL + path
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else None
    except Exception as exc:
        logger.error("get_open_position failed: %s", exc)
        return None


def set_credentials(key: str, secret: str) -> None:
    """Set API credentials for subsequent requests."""
    global API_KEY, API_SECRET
    API_KEY = key
    API_SECRET = secret


def check_credentials() -> bool:
    """Verify that the current credentials are valid."""
    path = "/api/v1/position"
    params = {"filter": json.dumps({"symbol": SYMBOL}), "count": 1}
    query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    try:
        headers = _make_headers("GET", path + query)
    except Exception as exc:
        logger.error("check_credentials failed: %s", exc)
        return False
    url = BASE_URL + path
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        return resp.status_code == 200
    except Exception as exc:
        logger.error("check_credentials failed: %s", exc)
        return False

