"""dYdX v4 exchange adapter."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

from exchange_interface import ExchangeAdapter

try:  # pragma: no cover - optional dependency
    from dydx4.clients import CompositeClient, constants, Subaccount
    from dydx4.clients.helpers.chain_helpers import (
        OrderSide,
        OrderType,
        OrderTimeInForce,
        OrderExecution,
    )
    from dydx4.chain.aerial.wallet import LocalWallet
    DYDX_AVAILABLE = True
except Exception:  # pragma: no cover - missing package
    CompositeClient = None
    constants = None
    Subaccount = None
    OrderSide = None
    OrderType = None
    OrderTimeInForce = None
    OrderExecution = None
    LocalWallet = None
    DYDX_AVAILABLE = False


class DYDXTrader(ExchangeAdapter):
    """Adapter for the dYdX v4 perpetual exchange."""

    def __init__(self, private_key: str, network: str = "mainnet", subaccount: int = 0) -> None:
        if not DYDX_AVAILABLE:
            raise ImportError("dydx4 package not installed")
        if network == "mainnet":
            net = constants.Network.mainnet()
        else:
            net = constants.Network.testnet()
        wallet = LocalWallet.from_unsafe_seed(private_key)
        self.subaccount = Subaccount(wallet, subaccount)
        self.client = CompositeClient(net)
        self.indexer = self.client.indexer_client
        logging.info("dYdX Trader initialisiert für %s", network)

    # ------------------------------------------------------------------
    # ExchangeAdapter interface
    # ------------------------------------------------------------------
    def fetch_markets(self) -> Dict[str, Any]:
        try:
            res = self.indexer.markets.get_perpetual_markets()
            return res.data
        except Exception as exc:  # pragma: no cover - network
            logging.error("dYdX markets Fehler: %s", exc)
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
        order_side = OrderSide.BUY if side.lower() in {"buy", "long"} else OrderSide.SELL
        price = price or 0
        try:
            tx = self.client.place_order(
                subaccount=self.subaccount,
                market=market,
                type=OrderType.MARKET,
                side=order_side,
                price=price,
                size=size,
                client_id=int(time.time()),
                time_in_force=OrderTimeInForce.IOC,
                good_til_block=0,
                good_til_time_in_seconds=30,
                execution=OrderExecution.IOC,
                post_only=False,
                reduce_only=reduce_only,
            )
            return {"success": True, "tx": tx.tx_hash}
        except Exception as exc:  # pragma: no cover - network
            logging.error("dYdX Orderfehler: %s", exc)
            return {"success": False, "error": str(exc)}

    def cancel_order(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        try:
            tx = self.client.cancel_order(
                self.subaccount,
                client_id=int(order_id),
                market=market or "",
                order_flags=0,
                good_til_time_in_seconds=30,
                good_til_block=0,
            )
            return {"success": True, "tx": tx.tx_hash}
        except Exception as exc:  # pragma: no cover - network
            logging.error("dYdX Cancel Fehler: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_order_status(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        try:
            res = self.indexer.account.get_order(order_id)
            return res.data
        except Exception as exc:  # pragma: no cover - network
            logging.error("dYdX Status Fehler: %s", exc)
            return {}

    def fetch_positions(self) -> Dict[str, Any]:
        try:
            res = self.indexer.account.get_subaccount_perpetual_positions(
                address=self.subaccount.address,
                subaccount_number=self.subaccount.subaccount_number,
            )
            return res.data
        except Exception as exc:  # pragma: no cover - network
            logging.error("dYdX Positions Fehler: %s", exc)
            return {}

    def fetch_funding_rate(self, market: str) -> Dict[str, Any]:
        try:
            res = self.indexer.markets.get_perpetual_market_funding(market)
            return res.data
        except Exception as exc:  # pragma: no cover - network
            logging.error("dYdX Funding Fehler: %s", exc)
            return {}


# ------------------------------------------------------------
# Helper to detect credentials
# ------------------------------------------------------------

def is_dydx_configured(settings: Dict[str, Any]) -> bool:
    """Return ``True`` if dYdX credentials are available."""
    key_env = os.getenv("DYDX_PRIVATE_KEY")
    if key_env:
        return True
    return bool(settings.get("dydx_private_key"))

