# data_provider.py
#
# Changelog:
# - Added type hints and improved docstrings
# - Replaced direct requests calls with a reusable session
# - Improved error handling and logging setup

from __future__ import annotations

import logging
from typing import List, Optional, TypedDict

import time

from binance_ws import BinanceWebSocket, BinanceCandleWebSocket
from tkinter import Tk, StringVar


# WebSocket manager and price cache
_WS_CLIENT: BinanceWebSocket | None = None
_WS_PRICE: dict[str, float] = {}
_WEBSOCKET_RUNNING: bool = False

_WS_STARTED: bool = False
_CANDLE_WS_CLIENT: BinanceCandleWebSocket | None = None
_CANDLE_WS_STARTED: bool = False
_WS_CANDLES: list["Candle"] = []
_CANDLE_WARNING_SHOWN: bool = False

# Tk root used for Tkinter variables when none is provided
_TK_ROOT: Tk | None = None


# Tkinter variable updated by the WebSocket callback
price_var: StringVar | None = None


def init_price_var(master=None) -> None:
    """Initialize ``price_var`` ensuring there is a valid ``Tk`` root."""
    global price_var, _TK_ROOT
    if master is None:
        if _TK_ROOT is None:
            _TK_ROOT = Tk()
        master = _TK_ROOT
    else:
        _TK_ROOT = master

    if price_var is None:
        price_var = StringVar(master=master, value="--")


def start_websocket(symbol: str = "BTCUSDT") -> None:
    """Start the websocket feed once and cache the latest price."""
    global _WS_STARTED, _WS_CLIENT
    if _WS_STARTED:
        return

    def handle(price: str) -> None:
        """Callback for websocket price updates."""
        global _WEBSOCKET_RUNNING
        try:
            p = float(price)
            _WS_PRICE[symbol] = p
            _WEBSOCKET_RUNNING = True
            if price_var is not None and _TK_ROOT is not None:
                _TK_ROOT.after(0, lambda val=price: price_var.set(str(val)))
            else:
                print("[WebSocket] \u274c price_var ist nicht initialisiert")
            try:
                import global_state
                global_state.last_feed_time = time.time()
            except Exception:
                pass
        except Exception as e:  # pragma: no cover - just log
            print("❌ WebSocket Fehler", e)

    _WS_CLIENT = BinanceWebSocket(handle)
    _WS_CLIENT.start()
    _WS_STARTED = True
    print("✅ WebSocket verbunden: Binance BTCUSDT")


def stop_websocket() -> None:
    """Stop the running websocket connection if active."""
    global _WS_CLIENT, _WS_STARTED, _WEBSOCKET_RUNNING
    if _WS_CLIENT is None:
        return
    try:
        _WS_CLIENT.stop()
    except Exception:
        pass
    _WS_CLIENT = None
    _WS_STARTED = False
    _WEBSOCKET_RUNNING = False


def start_candle_websocket(symbol: str = "BTCUSDT", interval: str = "1m") -> None:
    """Start candle websocket feed for *symbol* and *interval*."""
    global _CANDLE_WS_STARTED, _CANDLE_WS_CLIENT
    if _CANDLE_WS_STARTED:
        return

    print("INFO WebSocket Candle-Stream gestartet")

    def handle(candle: dict) -> None:
        update_candle_feed(candle)
        print(
            f"✅ Candle empfangen: Open={candle['open']}, Close={candle['close']}, Vol={candle['volume']}"
        )

    _CANDLE_WS_CLIENT = BinanceCandleWebSocket(handle)
    _CANDLE_WS_CLIENT.start()
    _CANDLE_WS_STARTED = True


def stop_candle_websocket() -> None:
    """Stop running candle websocket if active."""
    global _CANDLE_WS_CLIENT, _CANDLE_WS_STARTED
    if _CANDLE_WS_CLIENT is None:
        return
    try:
        _CANDLE_WS_CLIENT.stop()
    except Exception:
        pass
    _CANDLE_WS_CLIENT = None
    _CANDLE_WS_STARTED = False


def is_websocket_running() -> bool:
    """Return ``True`` if the websocket manager is active."""
    return _WEBSOCKET_RUNNING


def websocket_active() -> bool:
    """Return ``True`` if a websocket stream is delivering prices."""
    return _WEBSOCKET_RUNNING



def _fetch_ws_price(symbol: str) -> Optional[float]:
    """Return latest price from websocket if available."""
    global _WEBSOCKET_RUNNING
    if not _WS_STARTED:
        start_websocket(symbol)
    price = _WS_PRICE.get(symbol)
    _WEBSOCKET_RUNNING = price is not None
    return price

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


def update_candle_feed(candle: Candle) -> None:
    """Store *candle* in the internal cache and update feed timestamp."""
    global _WS_CANDLES, _WEBSOCKET_RUNNING
    _WS_CANDLES.append(candle)
    if len(_WS_CANDLES) > 1000:
        _WS_CANDLES.pop(0)
    _WEBSOCKET_RUNNING = True
    try:
        import global_state
        global_state.last_feed_time = time.time()
    except Exception:
        pass




def fetch_last_price(exchange: str = "binance", symbol: Optional[str] = None) -> Optional[float]:
    """Return the latest price from Binance Spot.

    For unsupported exchanges ``None`` is returned silently.
    """
    if exchange.lower() != "binance":
        logging.debug("Ignoring price request for unsupported exchange %s", exchange)
        return None

    pair = _normalize_symbol(symbol or "BTCUSDT")

    price = _fetch_ws_price(pair)
    if price is not None:
        return price

    return None

def get_latest_candle_batch(
    symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 100
) -> List[Candle]:
    """Return a batch of recent candles for *symbol* and *interval*."""
    return get_live_candles(symbol, interval, limit)

def get_live_candles(symbol: str, interval: str, limit: int) -> List[Candle]:
    """Retrieve recent candles from Binance Spot via WebSocket."""
    if not _CANDLE_WS_STARTED:
        start_candle_websocket(symbol, interval)
    return _WS_CANDLES[-limit:]


def fetch_latest_candle(symbol: str = "BTCUSDT", interval: str = "1m") -> Optional[Candle]:
    """Convenience helper returning only the latest candle."""
    candles = get_latest_candle_batch(symbol, interval, 1)
    return candles[-1] if candles else None
