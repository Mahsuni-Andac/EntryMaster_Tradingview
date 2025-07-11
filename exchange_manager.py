import os
import logging
from typing import Any, Dict, Type

from exchange_interface import ExchangeAdapter
from console_status import print_info

from mexc_trader import MEXCTrader
from dydx_trader import DYDXTrader, is_dydx_configured
from bitmex_trader import BitmexTrader

try:
    from binance_trader import BinanceTrader
except Exception:  # pragma: no cover - optional
    BinanceTrader = None

try:
    from bybit_trader import BybitTrader
except Exception:  # pragma: no cover - optional
    BybitTrader = None


def detect_available_exchanges(settings: Dict[str, Any]) -> Dict[str, Type[ExchangeAdapter]]:
    """Detect and return available exchange adapters based on credentials."""
    available: Dict[str, Type[ExchangeAdapter]] = {}

    if os.getenv("MEXC_API_KEY") and os.getenv("MEXC_API_SECRET"):
        available["mexc"] = MEXCTrader
    elif settings.get("mexc_key") and settings.get("mexc_secret"):
        available["mexc"] = MEXCTrader
    else:
        print_info("MEXC deaktiviert - keine Zugangsdaten")

    if is_dydx_configured(settings):
        available["dydx"] = DYDXTrader
    else:
        print_info("dYdX deaktiviert - keine Zugangsdaten")

    if os.getenv("BITMEX_API_KEY") and os.getenv("BITMEX_API_SECRET"):
        available["bitmex"] = BitmexTrader
    elif settings.get("bitmex_key") and settings.get("bitmex_secret"):
        available["bitmex"] = BitmexTrader
    else:
        print_info("BitMEX deaktiviert - keine Zugangsdaten")

    if BinanceTrader and (
        (os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_API_SECRET"))
        or (settings.get("binance_key") and settings.get("binance_secret"))
    ):
        available["binance"] = BinanceTrader
    elif BinanceTrader:
        print_info("Binance deaktiviert - keine Zugangsdaten")

    if BybitTrader and (
        (os.getenv("BYBIT_API_KEY") and os.getenv("BYBIT_API_SECRET"))
        or (settings.get("bybit_key") and settings.get("bybit_secret"))
    ):
        available["bybit"] = BybitTrader
    elif BybitTrader:
        print_info("Bybit deaktiviert - keine Zugangsdaten")

    print_info(
        "Aktive Exchanges: " + (", ".join(available.keys()) if available else "keine")
    )
    return available
