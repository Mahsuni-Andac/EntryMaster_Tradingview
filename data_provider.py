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
from binance import ThreadedWebsocketManager  # for optional WebSocket feed

from config import SETTINGS

_BINANCE = Client("", "")
# WebSocket manager and price cache used when ``data_source_mode`` is
# set to ``websocket`` or ``auto``.
_WS_MANAGER: ThreadedWebsocketManager | None = None
_WS_PRICE: dict[str, float] = {}


def _init_websocket(symbol: str) -> None:
    """Start a websocket price feed for *symbol* if not running."""
    global _WS_MANAGER
    if _WS_MANAGER is not None:
        return
    try:
        _WS_MANAGER = ThreadedWebsocketManager()
        _WS_MANAGER.start()

        def handle(msg):
            if msg.get("e") == "error":
                return
            price = msg.get("c") or msg.get("p")
            if price is not None:
                _WS_PRICE[symbol] = float(price)

        _WS_MANAGER.start_symbol_ticker_socket(symbol.lower(), handle)
    except Exception as exc:
        logging.debug("WebSocket init failed: %s", exc)
        _WS_MANAGER = None


def _fetch_ws_price(symbol: str) -> Optional[float]:
    """Return latest price from websocket if available."""
    if _WS_MANAGER is None:
        _init_websocket(symbol)
    return _WS_PRICE.get(symbol)

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
    """Return the latest price from Binance Spot.

    For unsupported exchanges ``None`` is returned silently.
    """
    if exchange.lower() != "binance":
        logging.debug("Ignoring price request for unsupported exchange %s", exchange)
        return None

    pair = _normalize_symbol(symbol or "BTCUSDT")
    mode = SETTINGS.get("data_source_mode", "rest").lower()

    if mode in {"websocket", "auto"}:
        price = _fetch_ws_price(pair)
        if price is not None:
            return price
        if mode == "websocket":
            return None

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
    mode = SETTINGS.get("data_source_mode", "rest").lower()

    if mode in {"websocket", "auto"}:
        # placeholder: websocket candle feed not yet implemented
        if mode == "websocket":
            return []

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
