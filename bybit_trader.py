from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from exchange_interface import ExchangeAdapter


class BybitTrader(ExchangeAdapter):
    """Minimal Bybit adapter placeholder."""

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        logging.info("BybitTrader initialisiert")

    def fetch_markets(self) -> Dict[str, Any]:
        return {}

    def place_order(
        self,
        market: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        reduce_only: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        raise NotImplementedError("Bybit API nicht implementiert")

    def cancel_order(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def get_order_status(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def fetch_positions(self) -> Dict[str, Any]:
        return {}

    def fetch_funding_rate(self, market: str) -> Dict[str, Any]:
        return {}
