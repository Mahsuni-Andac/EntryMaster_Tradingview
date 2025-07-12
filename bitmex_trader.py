from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from symbol_utils import bitmex_symbol

import requests

from exchange_interface import ExchangeAdapter


class BitmexTrader(ExchangeAdapter):
    """Thin wrapper around the BitMEX REST API."""

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://www.bitmex.com/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "api-key": self.api_key,
            "api-secret": self.api_secret,
        })
        logging.info("BitMEX Trader initialisiert")

    def get_market_price(self, symbol: str = "XBTUSD") -> Optional[float]:
        """Return the latest market price for *symbol*."""
        symbol = bitmex_symbol(symbol)
        try:
            url = f"{self.base_url}/instrument?symbol={symbol}"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return float(data[0]["lastPrice"])
        except Exception as exc:
            logging.error("BitMEX Preisabruf fehlgeschlagen: %s", exc)
            return None

    def _get(self, path: str, **params: Any) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}{path}"
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # pragma: no cover - network failures
            logging.error("BitMEX GET Fehler: %s", exc)
            return {}

    def fetch_markets(self) -> Dict[str, Any]:
        return self._get("/instrument/active")

    def place_order(
        self,
        market: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        reduce_only: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        raise NotImplementedError("BitMEX API nicht implementiert")

    def cancel_order(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def get_order_status(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def fetch_positions(self) -> Dict[str, Any]:
        return {}

    def fetch_funding_rate(self, market: str) -> Dict[str, Any]:
        market = bitmex_symbol(market)
        params = {"symbol": market, "count": 1, "reverse": "true"}
        return self._get("/funding", **params)
