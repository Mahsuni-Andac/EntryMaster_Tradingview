import os
import time
import hmac
import hashlib
import json
import logging
from typing import Optional

import requests


class BitmexClient:
    """Thin REST client for BitMEX Testnet."""

    def __init__(self,
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 base_url: str = "https://testnet.bitmex.com") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("BITMEX_API_KEY")
        self.api_secret = api_secret or os.getenv("BITMEX_API_SECRET")
        self.symbol = "XBTUSD"
        self.logger = logging.getLogger(__name__)

    # internal helper to create request headers
    def _headers(self, verb: str, endpoint: str, data: str = "") -> dict:
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not set")
        expires = str(int(time.time()) + 5)
        message = verb + endpoint + expires + data
        signature = hmac.new(
            self.api_secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        return {
            "api-expires": expires,
            "api-key": self.api_key,
            "api-signature": signature,
            "Content-Type": "application/json",
        }

    # basic request helper
    def _request(self, verb: str, endpoint: str, *, data: Optional[dict] = None) -> dict:
        body = json.dumps(data) if data else ""
        headers = self._headers(verb, endpoint, body)
        url = self.base_url + endpoint
        response = requests.request(verb, url, headers=headers, data=body, timeout=10)
        response.raise_for_status()
        return response.json()

    def place_order(self, side: str, quantity: float, reduce_only: bool = False) -> dict:
        side = side.upper()
        payload = {
            "symbol": self.symbol,
            "orderQty": quantity,
            "side": side,
            "ordType": "Market",
        }
        if reduce_only:
            payload["execInst"] = "ReduceOnly"
        return self._request("POST", "/api/v1/order", data=payload)

    def get_open_position(self) -> Optional[dict]:
        data = self._request("GET", "/api/v1/position")
        for pos in data:
            if pos.get("symbol") == self.symbol:
                return pos
        return None

    def close_position(self) -> Optional[dict]:
        pos = self.get_open_position()
        if not pos or not pos.get("currentQty"):
            return None
        side = "Sell" if pos["currentQty"] > 0 else "Buy"
        return self.place_order(side, abs(pos["currentQty"]), reduce_only=True)
