## Changelog
# - Added logging and reusable requests session
# - Added type hints and request timeout constant
# - Improved error handling and docstrings

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from exchange_interface import ExchangeAdapter

import requests


TIMEOUT = 10


class MEXCTrader(ExchangeAdapter):
    """Thin wrapper around the MEXC REST API."""

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://contract.mexc.com/api/v1"
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "ApiKey": self.api_key,
        }
        self.active_orders: list[str] = []

    def get_market_price(self, symbol: str) -> Optional[float]:
        """Return the latest market price for *symbol*."""
        if not self.api_key or not self.api_secret:
            logging.error("MEXC API-Key fehlt")
            return None
        try:
            url = f"{self.base_url}/contract/ticker?symbol={symbol}"
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if not data or "data" not in data or not data["data"]:
                raise ValueError(f"Antwort ohne Marktdaten: {data}")
            payload = data["data"]
            if isinstance(payload, list):
                payload = payload[0]
            return float(payload["lastPrice"])
        except Exception as exc:
            logging.error("Fehler beim Abrufen des Marktpreises: %s", exc)
            return None

    def place_order(self, symbol: str, side: str, amount: float, leverage: int) -> Dict[str, Any]:
        """Place a market order and return the raw API response."""
        try:
            market_price = self.get_market_price(symbol)
            if market_price is None:
                return {"success": False, "error": "Kein Marktpreis verf\u00fcgbar"}

            order_data = {
                "symbol": symbol,
                "side": side.upper(),
                "type": "MARKET",
                "quantity": round(amount, 6),
                "price": market_price,
                "leverage": leverage,
            }

            url = f"{self.base_url}/private/order/submit"
            response = self.session.post(url, headers=self.headers, json=order_data, timeout=TIMEOUT)
            result = response.json()

            if "orderId" in result:
                self.active_orders.append(str(result["orderId"]))
                logging.info(
                    "Order ausgef\u00fchrt: %s %s %s @ %.2f",
                    side.upper(),
                    amount,
                    symbol,
                    market_price,
                )
                return {"success": True, "order_id": result["orderId"], "price": market_price, "amount": amount, "side": side.upper()}

            logging.warning("Orderantwort enth\u00e4lt keine Order-ID: %s", result)
            return {"success": False, "error": "Keine Order-ID in Antwort", "raw": result}
        except Exception as exc:
            logging.error("Fehler bei Orderplatzierung: %s", exc)
            return {"success": False, "error": str(exc)}

    def place_sl_tp_orders(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        sl: float,
        tp: float,
        amount: float,
    ) -> Dict[str, Any]:
        """Place stop-loss and take-profit orders for an open position."""
        try:
            opposite = "SELL" if side.upper() == "BUY" else "BUY"
            url = f"{self.base_url}/private/order/submit"

            tp_order = {
                "symbol": symbol,
                "side": opposite,
                "type": "TAKE_PROFIT_MARKET",
                "stopPrice": round(tp, 2),
                "quantity": round(amount, 6),
            }
            sl_order = {
                "symbol": symbol,
                "side": opposite,
                "type": "STOP_MARKET",
                "stopPrice": round(sl, 2),
                "quantity": round(amount, 6),
            }

            tp_result = self.session.post(url, headers=self.headers, json=tp_order, timeout=TIMEOUT).json()
            sl_result = self.session.post(url, headers=self.headers, json=sl_order, timeout=TIMEOUT).json()

            logging.info("TP-Order gesendet: %s", tp_result)
            logging.info("SL-Order gesendet: %s", sl_result)

            return {"success": True, "tp_result": tp_result, "sl_result": sl_result}
        except Exception as exc:
            logging.error("Fehler bei SL/TP Orders: %s", exc)
            return {"success": False, "error": str(exc)}

    def cancel_order(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an existing order by its ID."""
        try:
            url = f"{self.base_url}/private/order/cancel"
            payload = {"orderId": order_id}
            result = self.session.post(url, headers=self.headers, json=payload, timeout=TIMEOUT).json()
            logging.info("Order %s abgebrochen: %s", order_id, result)
            return {"success": True, "result": result}
        except Exception as exc:
            logging.error("Fehler beim Orderabbruch: %s", exc)
            return {"success": False, "error": str(exc)}

    def close_position_market(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        """Close a position using a market order."""
        try:
            close_side = "SELL" if side.upper() == "BUY" else "BUY"
            order_data = {
                "symbol": symbol,
                "side": close_side,
                "type": "MARKET",
                "quantity": round(amount, 6),
            }
            url = f"{self.base_url}/private/order/submit"
            result = self.session.post(url, headers=self.headers, json=order_data, timeout=TIMEOUT).json()
            logging.info("Position geschlossen via MARKET: %s", result)
            return {"success": True, "result": result}
        except Exception as exc:
            logging.error("Fehler beim Schlie\u00dfen der Position: %s", exc)
            return {"success": False, "error": str(exc)}

    # --- ExchangeAdapter interface methods ---

    def fetch_markets(self) -> Dict[str, Any]:
        """Return available futures markets."""
        try:
            resp = self.session.get(f"{self.base_url}/../api/v3/exchangeInfo", timeout=TIMEOUT)
            return resp.json()
        except Exception as exc:  # pragma: no cover - network failures
            logging.error("Fehler beim Abrufen der Marktdaten: %s", exc)
            return {}


    def get_order_status(self, order_id: str, market: Optional[str] = None) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/private/order/query"
            payload = {"orderId": order_id}
            result = self.session.get(url, headers=self.headers, params=payload, timeout=TIMEOUT).json()
            return result
        except Exception as exc:
            logging.error("Fehler beim Abrufen Orderstatus: %s", exc)
            return {"success": False, "error": str(exc)}

    def fetch_positions(self) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/private/position/open_positions"
            result = self.session.get(url, headers=self.headers, timeout=TIMEOUT).json()
            return result
        except Exception as exc:
            logging.error("Fehler beim Abrufen Positionen: %s", exc)
            return {}

    def fetch_funding_rate(self, market: str) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/private/funding/prevFundingRate"
            result = self.session.get(url, headers=self.headers, params={"symbol": market}, timeout=TIMEOUT).json()
            return result
        except Exception as exc:  # pragma: no cover - network failures
            logging.error("Fehler bei Fundingrate: %s", exc)
            return {}

