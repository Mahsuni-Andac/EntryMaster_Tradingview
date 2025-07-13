# exchange_interface.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ExchangeAdapter(ABC):

    @abstractmethod
    def fetch_markets(self) -> Any:

    @abstractmethod
    def place_order(
        self,
        market: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        reduce_only: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:

    @abstractmethod
    def cancel_order(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:

    @abstractmethod
    def get_order_status(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:

    @abstractmethod
    def fetch_positions(self) -> Any:

    @abstractmethod
    def fetch_funding_rate(self, market: str) -> Any:

