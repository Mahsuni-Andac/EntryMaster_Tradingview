"""Beispiel für automatische dYdX-Initialisierung."""

import os
from config import SETTINGS
from init_helpers import import_trader

# Annahme: SETTINGS enthält 'trading_backend' = 'dydx'

if __name__ == "__main__":
    Trader = import_trader(SETTINGS.get("trading_backend", "sim"))
    trader = Trader(os.getenv("DYDX_PRIVATE_KEY") or SETTINGS.get("dydx_private_key"))

    markets = trader.fetch_markets()
    print("verfügbare Märkte:", list(markets.get("markets", {}).keys()))

    # Beispielorder
    result = trader.place_order(market="BTC-USD", side="buy", size=1.0)
    print("Orderergebnis:", result)
