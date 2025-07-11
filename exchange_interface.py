from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ExchangeAdapter(ABC):
    """Base interface for all exchange adapters."""

    @abstractmethod
    def fetch_markets(self) -> Any:
        """Return available trading pairs/markets."""

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
        """Place an order on the exchange."""

    @abstractmethod
    def cancel_order(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an existing order."""

    @abstractmethod
    def get_order_status(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve current order status."""

    @abstractmethod
    def fetch_positions(self) -> Any:
        """Return current open positions."""

    @abstractmethod
    def fetch_funding_rate(self, market: str) -> Any:
        """Return funding rate information for *market*."""

