# data_provider.py
#
# Changelog:
# - Added type hints and improved docstrings
# - Replaced direct requests calls with a reusable session
# - Improved error handling and logging setup

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Iterable, List, Optional, TypedDict

import requests

from config import SETTINGS


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
    now = datetime.now().strftime("%H:%M:%S")
    try:
        resp = _SESSION.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:  # pragma: no cover - network failures
        msg = f"{query_symbol}: -- ({now}) | ERROR: Request failed: {exc}"
        logging.error(msg)
        print(msg)
        return None

    try:
        data = resp.json()
    except Exception as exc:
        msg = f"{query_symbol}: -- ({now}) | ERROR: Response not JSON: {exc}"
        logging.error(msg)
        print(msg)
        return None

    json_dump = json.dumps(data, ensure_ascii=False)
    logging.info("%s FULL RESPONSE: %s", exchange.upper(), json_dump)
    print(json_dump)

    if isinstance(data, dict) and data.get("success") is False:
        code = data.get("code", "?")
        err = data.get("message", "Unknown error")
        msg = f"{query_symbol}: -- ({now}) | ERROR: [code: {code}] {err}"
        logging.error(msg)
        print(msg)
        if exchange.lower() == "mexc":
            print("👉 Verfügbare Symbole: https://contract.mexc.com/api/v1/contract/detail")
        return None

    if isinstance(data, dict) and "data" not in data:
        msg = f"{query_symbol}: -- ({now}) | ERROR: 'data' fehlt in Antwort"
        logging.error(msg)
        print(msg)
        if exchange.lower() == "mexc":
            print("👉 Verfügbare Symbole: https://contract.mexc.com/api/v1/contract/detail")
        return None

    val = data
    try:
        for key in info["path"]:
            if isinstance(key, int):
                if not isinstance(val, list) or len(val) <= key:
                    raise KeyError(key)
                val = val[key]
            else:
                if not isinstance(val, dict) or key not in val:
                    raise KeyError(key)
                val = val[key]
        price = float(val)
    except KeyError as exc:
        msg = f"{query_symbol}: -- ({now}) | ERROR: Key '{exc.args[0]}' fehlt"
        logging.error(msg)
        print(msg)
        return None
    except Exception as exc:
        msg = f"{query_symbol}: -- ({now}) | ERROR: {exc}"
        logging.error(msg)
        print(msg)
        return None

    msg = f"{query_symbol}: {price:.2f} ({now})"
    logging.info(msg)
    print(msg)
    return price

def get_latest_candle_batch(
    symbol: str = "BTC_USDT", interval: str = "1m", limit: int = 100
) -> List[Candle]:
    """Return a batch of recent candles for *symbol* and *interval*."""
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
                try:
                    candles.append({
                        "timestamp": int(row[0]),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5])
                    })
                except Exception as exc:
                    raise ValueError(f"Row error {row}: {exc}") from exc
            return candles
        except Exception as e:
            logging.warning(f"[{name.upper()}] Fehler beim Abrufen von Candle-Daten: {e}")

    logging.error("❌ Beide Anbieter (MEXC & Binance) fehlgeschlagen.")
    return []


def fetch_latest_candle(symbol: str = "BTC_USDT", interval: str = "1m") -> Optional[Candle]:
    """Convenience helper returning only the latest candle."""
    candles = get_latest_candle_batch(symbol, interval, 1)
    return candles[-1] if candles else None
