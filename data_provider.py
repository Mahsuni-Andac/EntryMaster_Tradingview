# data_provider.py
#
# Changelog:
# - Added type hints and improved docstrings
# - Replaced direct requests calls with a reusable session
# - Improved error handling and logging setup

from __future__ import annotations

import csv
import logging
import os
from typing import Iterable, List, Optional, TypedDict

import requests

from config import SETTINGS



SIM_DATA_PATH: str = SETTINGS.get("sim_data_path", "sim_data.csv")


class Candle(TypedDict):
    """Typed representation of a OHLCV candle."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


_SESSION = requests.Session()

# Mapping for simple ticker price retrieval per exchange
PRICE_FEEDS = {
    "mexc": {
        "symbol": "BTC_USDT",
        "url": "https://contract.mexc.com/api/v1/contract/ticker?symbol={symbol}",
        "path": ["data", "lastPrice"],
    },
    "bitmex": {
        "symbol": "XBTUSD",
        "url": "https://www.bitmex.com/api/v1/instrument?symbol={symbol}",
        "path": [0, "lastPrice"],
    },
}

def fetch_last_price(exchange: str, symbol: Optional[str] = None) -> Optional[float]:
    """Return the latest price for *exchange* using the REST API.

    Supported exchanges are defined in ``PRICE_FEEDS``.  The mapping includes
    the default symbol, endpoint URL and JSON path to the ``lastPrice`` field.
    When *symbol* is given it overrides the default symbol.  For BitMEX the
    value is converted via :func:`bitmex_symbol`.
    """
    if exchange.lower() == "sim":
        price = fetch_simulated_price()
        if price is not None:
            logging.info("Sim-Modus aktiv: Marktdaten aus Datei '%s' geladen", SIM_DATA_PATH)
        else:
            logging.warning("Warnung: Keine Simulationsdaten gefunden!")
        return price
    info = PRICE_FEEDS.get(exchange.lower())
    if not info:
        raise ValueError(f"Unknown exchange '{exchange}'")

    query_symbol = symbol or info["symbol"]
    if symbol:
        query_symbol = query_symbol.replace("_", "")
        if exchange.lower() == "bitmex":
            from symbol_utils import bitmex_symbol

            query_symbol = bitmex_symbol(query_symbol)

    url = info["url"].format(symbol=query_symbol)
    try:
        resp = _SESSION.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        val = data
        for key in info["path"]:
            val = val[key]
        price = float(val)
        logging.info("Marktdaten empfangen: %s %.2f", exchange.upper(), price)
        return price
    except Exception as exc:  # pragma: no cover - network failures
        logging.error("%s Preisabruf fehlgeschlagen: %s", exchange.upper(), exc)
        return None

def get_latest_candle_batch(
    symbol: str = "BTC_USDT", interval: str = "1m", limit: int = 100
) -> List[Candle]:
    """Return a batch of recent candles for *symbol* and *interval*."""
    if SETTINGS.get("test_mode"):
        return get_simulated_candles(limit)
    return get_live_candles(symbol, interval, limit)

def get_live_candles(symbol: str, interval: str, limit: int) -> List[Candle]:
    """Retrieve candles from public exchanges with failover."""
    spot_symbol = symbol.replace("_", "")
    backends = [
        (
            "mexc",
            f"https://api.mexc.com/api/v3/klines?symbol={spot_symbol}&interval={interval}&limit={limit}",
        ),
        (
            "binance",
            f"https://api.binance.com/api/v3/klines?symbol={spot_symbol}&interval={interval}&limit={limit}",
        ),
    ]

    for name, url in backends:
        try:
            response = _SESSION.get(url, timeout=10)
            response.raise_for_status()
            raw = response.json()
            if not raw or not isinstance(raw, list):
                raise ValueError("Unerwartete API-Antwortstruktur")
            candles: List[Candle] = []
            for row in raw:
                candles.append({
                    "timestamp": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5])
                })
            return candles
        except Exception as e:
            logging.warning(f"[{name.upper()}] Fehler beim Abrufen von Candle-Daten: {e}")

    logging.error("❌ Beide Anbieter (MEXC & Binance) fehlgeschlagen.")
    return []

def get_simulated_candles(limit: int) -> List[Candle]:
    """Read candles from the simulation CSV file."""
    if not os.path.exists(SIM_DATA_PATH):
        logging.error("❌ Simulationsdatei '%s' nicht gefunden.", SIM_DATA_PATH)
        return []

    candles: List[Candle] = []
    try:
        with open(SIM_DATA_PATH, "r", newline="") as file:
            reader = list(csv.DictReader(file))
            if not reader:
                logging.warning("❌ Keine Simulationsdaten gefunden.")
                return []
            rows = reader[-limit:] if len(reader) >= limit else reader
            for row in rows:
                candles.append({
                    "timestamp": int(row["timestamp"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"])
                })
        return candles
    except Exception as e:
        logging.error(f"❌ Fehler beim Lesen der Simulationsdaten: {e}")
        return []

def fetch_simulated_price() -> Optional[float]:
    """Return the latest close price from the simulation data."""
    candles = get_simulated_candles(1)
    if not candles:
        return None
    return candles[-1]["close"]

def fetch_latest_candle(symbol: str = "BTC_USDT", interval: str = "1m") -> Optional[Candle]:
    """Convenience helper returning only the latest candle."""
    candles = get_latest_candle_batch(symbol, interval, 1)
    return candles[-1] if candles else None
