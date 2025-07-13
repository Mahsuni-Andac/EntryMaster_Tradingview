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

import time

from binance.client import Client
from binance_ws import BinanceWebSocket
from tkinter import Tk, StringVar

from config import SETTINGS

# Currently active feed source: websocket | rest | auto
current_feed_source = SETTINGS.get("data_source_mode", "auto").lower()

_BINANCE = Client("", "")
# WebSocket manager and price cache used when ``data_source_mode`` is
# set to ``websocket`` or ``auto``.
_WS_CLIENT: BinanceWebSocket | None = None
_WS_PRICE: dict[str, float] = {}
_WEBSOCKET_RUNNING: bool = False

_WS_STARTED: bool = False

# Tk root used for Tkinter variables when none is provided
_TK_ROOT: Tk | None = None

# REST polling handle
_REST_JOB: str | None = None
_REST_INTERVAL_MS = 1000
_REST_RUNNING = False

# Auto mode watchdog
_AUTO_JOB: str | None = None

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


def is_websocket_running() -> bool:
    """Return ``True`` if the websocket manager is active."""
    return _WEBSOCKET_RUNNING


def websocket_active() -> bool:
    """Return ``True`` if a websocket stream is delivering prices."""
    return _WEBSOCKET_RUNNING


def _rest_poll(symbol: str, interval: str) -> None:
    global _REST_JOB, _REST_RUNNING
    if _TK_ROOT is None:
        init_price_var()
    pair = _normalize_symbol(symbol)
    try:
        data = _BINANCE.get_symbol_ticker(symbol=pair)
        price = float(data["price"])
        _WS_PRICE[symbol] = price
        if price_var is not None and _TK_ROOT is not None:
            _TK_ROOT.after(0, lambda val=price: price_var.set(str(val)))
        try:
            import global_state
            global_state.last_feed_time = time.time()
        except Exception:
            pass
    except Exception:
        pass
    if _TK_ROOT is not None:
        _REST_JOB = _TK_ROOT.after(_REST_INTERVAL_MS, _rest_poll, symbol, interval)
    _REST_RUNNING = True


def start_rest_timer(symbol: str = "BTCUSDT", interval: str = "1m") -> None:
    global _REST_RUNNING
    if _REST_RUNNING:
        return
    if _TK_ROOT is None:
        init_price_var()
    _rest_poll(symbol, interval)


def cancel_rest_timer() -> None:
    global _REST_JOB, _REST_RUNNING
    if _REST_JOB and _TK_ROOT is not None:
        try:
            _TK_ROOT.after_cancel(_REST_JOB)
        except Exception:
            pass
    _REST_JOB = None
    _REST_RUNNING = False


def _auto_loop(symbol: str, interval: str, timeout: int = 5) -> None:
    global _AUTO_JOB
    if _TK_ROOT is None:
        init_price_var()
    ws_ok = websocket_active()
    last = None
    try:
        import global_state
        last = global_state.last_feed_time
    except Exception:
        pass
    if ws_ok:
        cancel_rest_timer()
    else:
        if last is None or time.time() - last > timeout:
            start_rest_timer(symbol, interval)
    if _TK_ROOT is not None:
        _AUTO_JOB = _TK_ROOT.after(1000, _auto_loop, symbol, interval, timeout)


def stop_auto_mode() -> None:
    global _AUTO_JOB
    if _AUTO_JOB and _TK_ROOT is not None:
        try:
            _TK_ROOT.after_cancel(_AUTO_JOB)
        except Exception:
            pass
    _AUTO_JOB = None
    cancel_rest_timer()
    stop_websocket()


def start_auto_mode(symbol: str = "BTCUSDT", interval: str = "1m") -> None:
    start_websocket(symbol)
    _auto_loop(symbol, interval)


def switch_feed_source(mode: str, symbol: str = "BTCUSDT", interval: str = "1m") -> None:
    """Switch active data source ensuring only one is running."""
    global current_feed_source
    if mode == current_feed_source:
        return
    if current_feed_source == "websocket":
        stop_websocket()
    elif current_feed_source == "rest":
        cancel_rest_timer()
    elif current_feed_source == "auto":
        stop_auto_mode()

    current_feed_source = mode
    SETTINGS["data_source_mode"] = mode
    if mode == "websocket":
        start_websocket(symbol)
    elif mode == "rest":
        start_rest_timer(symbol, interval)
    else:
        start_auto_mode(symbol, interval)



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




def fetch_last_price(exchange: str = "binance", symbol: Optional[str] = None) -> Optional[float]:
    """Return the latest price from Binance Spot.

    For unsupported exchanges ``None`` is returned silently.
    """
    if exchange.lower() != "binance":
        logging.debug("Ignoring price request for unsupported exchange %s", exchange)
        return None

    pair = _normalize_symbol(symbol or "BTCUSDT")
    mode = current_feed_source

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
        if price_var is not None and _TK_ROOT is not None:
            _TK_ROOT.after(0, lambda val=price: price_var.set(str(val)))
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
    mode = current_feed_source

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
