"""Einfacher Trading-Simulator für lokale Tests."""

from __future__ import annotations

import logging
from typing import Any, Dict

class SimTrader:
    """Simulation eines Traders ohne echte API-Aufrufe."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialisiert den Trader mit einer leeren Orderliste."""
        self.orders: list[Dict[str, Any]] = []

    def place_order(
        self,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        reduce_only: bool = False,
        order_type: str | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Erzeuge eine simulierte Order und speichere sie."""

        if stop_loss is None or take_profit is None:
            logging.warning("place_order ohne SL/TP aufgerufen")

        order = {
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reduce_only": reduce_only,
            "order_type": order_type,
            "status": "open",
        }
        self.orders.append(order)
        print(
            f"[SIM] {side.upper()} Order | Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit}, Size: {quantity}"
        )
        return {"success": True, "order": order}

    def close_position(self, *args: Any, **kwargs: Any) -> None:
        """Schließt eine simulierte Position."""
        print("[SIM] Position geschlossen.")

    def cancel_order(self, *args: Any, **kwargs: Any) -> None:
        """Storniert eine simulierte Order."""
        print("[SIM] Order storniert.")

    def place_sl_tp_orders(
        self,
        symbol: str,
        direction: str,
        entry: float,
        sl: float,
        tp: float,
        amount: float,
    ) -> Dict[str, Any]:
        """Im Sim-Modus nur eine Log-Ausgabe für SL/TP-Orders."""
        print(
            f"[SIM] SL/TP Orders gesetzt | Symbol: {symbol}, Dir: {direction}, Entry: {entry}, SL: {sl}, TP: {tp}, Size: {amount}"
        )
        return {"success": True}
