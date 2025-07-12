import os
import logging
from typing import Any, Dict, Type

from exchange_interface import ExchangeAdapter
from console_status import print_info

from bitmex_trader import BitmexTrader


def detect_available_exchanges(settings: Dict[str, Any]) -> Dict[str, Type[ExchangeAdapter]]:
    """Return available exchange adapters (only BitMEX)."""
    available: Dict[str, Type[ExchangeAdapter]] = {}

    if os.getenv("BITMEX_API_KEY") and os.getenv("BITMEX_API_SECRET"):
        available["bitmex"] = BitmexTrader
    elif settings.get("bitmex_key") and settings.get("bitmex_secret"):
        available["bitmex"] = BitmexTrader
    else:
        print_info("BitMEX deaktiviert - keine Zugangsdaten")

    print_info(
        "Aktive Exchanges: " + (", ".join(available.keys()) if available else "keine")
    )
    return available
