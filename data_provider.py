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

from binance.client import Client

from config import SETTINGS

_BINANCE = Client("", "")

def _normalize_symbol(symbol: str) -> str:
    """Return API-compatible symbol name for Binance."""
    return symbol.replace("/", "").replace("_", "").upper()


class Candle(TypedDict):
    """Typed representation of a OHLCV candle."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float




def fetch_last_price(exchange: str = "binance", symbol: Optional[str] = None) -> Optional[float]:
    """Return the latest price from Binance Spot."""
    if exchange.lower() != "binance":
        raise ValueError("Only Binance spot data supported")

    pair = _normalize_symbol(symbol or "BTCUSDT")
    try:
        data = _BINANCE.get_symbol_ticker(symbol=pair)
        price = float(data["price"])
        logging.debug("Price update %s: %.2f", pair, price)
        return price
    except Exception as exc:
        logging.debug("Failed to fetch %s: %s", pair, exc)
        return None

def get_latest_candle_batch(
    symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 100
) -> List[Candle]:
    """Return a batch of recent candles for *symbol* and *interval*."""
    return get_live_candles(symbol, interval, limit)

def get_live_candles(symbol: str, interval: str, limit: int) -> List[Candle]:
    """Retrieve recent candles from Binance Spot."""
    pair = _normalize_symbol(symbol)
    try:
        raw = _BINANCE.get_klines(symbol=pair, interval=interval, limit=limit)
        candles: List[Candle] = []
        for row in raw:
            candles.append({
                "timestamp": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        return candles
    except Exception as e:
        logging.error("Binance candle fetch failed: %s", e)
        return []


def fetch_latest_candle(symbol: str = "BTCUSDT", interval: str = "1m") -> Optional[Candle]:
    """Convenience helper returning only the latest candle."""
    candles = get_latest_candle_batch(symbol, interval, 1)
    return candles[-1] if candles else None
