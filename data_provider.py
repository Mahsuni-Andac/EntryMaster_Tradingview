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
import threading

import binance_ws


# WebSocket manager and price cache
_WS_CLIENT: binance_ws.BinanceWebSocket | None = None
_WS_PRICE: dict[str, float] = {}


class WebSocketStatus:
    """Simple class to store websocket running flag without globals."""

    running = False

    @classmethod
    def is_running(cls) -> bool:
        return cls.running

    @classmethod
    def set_running(cls, value: bool) -> None:
        cls.running = value

_WS_STARTED: bool = False
_CANDLE_WS_CLIENT: binance_ws.BinanceCandleWebSocket | None = None
_CANDLE_WS_STARTED: bool = False
_WS_CANDLES: list["Candle"] = []

_FEED_MONITOR_THREAD: threading.Thread | None = None
_FEED_MONITOR_STARTED: bool = False


def start_websocket(symbol: str = "BTCUSDT") -> None:
    """Start the websocket feed once and cache the latest price."""
    global _WS_STARTED, _WS_CLIENT
    if _WS_STARTED:
        return

    def handle(price: str) -> None:
        """Callback for websocket price updates."""
        try:
            p = float(price)
            _WS_PRICE[symbol] = p
            WebSocketStatus.set_running(True)
            try:
                import global_state
                global_state.last_feed_time = time.time()
            except Exception:
                pass
        except Exception as e:  # pragma: no cover - just log
            logging.error("WebSocket Fehler: %s", e)

    _WS_CLIENT = binance_ws.BinanceWebSocket(handle)
    _WS_CLIENT.start()
    _WS_STARTED = True
    logging.info("WebSocket verbunden: Binance BTCUSDT")


def stop_websocket() -> None:
    """Stop the running websocket connection if active."""
    global _WS_CLIENT, _WS_STARTED
    if _WS_CLIENT is None:
        return
    try:
        _WS_CLIENT.stop()
    except Exception:
        pass
    _WS_CLIENT = None
    _WS_STARTED = False
    WebSocketStatus.set_running(False)


def start_candle_websocket(symbol: str = "BTCUSDT", interval: str = "1m") -> None:
    """Start candle websocket feed for *symbol* and *interval*."""
    global _CANDLE_WS_STARTED, _CANDLE_WS_CLIENT
    if _CANDLE_WS_STARTED:
        logging.warning("Candle-WebSocket bereits gestartet")
        return

    logging.info("WebSocket Candle-Stream gestartet")

    # pass None so BinanceCandleWebSocket forwards candles to update_candle_feed
    _CANDLE_WS_CLIENT = binance_ws.BinanceCandleWebSocket(None, symbol=symbol, interval=interval)
    _CANDLE_WS_CLIENT.start()
    _CANDLE_WS_STARTED = True

    # wait up to 10 seconds for first candle to arrive
    start_time = time.time()
    while time.time() - start_time < 10:
        if _WS_CANDLES:
            logging.info("Erste Candle(s) empfangen – WebSocket läuft stabil")
            break
        time.sleep(0.5)
    else:
        logging.warning("Kein Candle-Update nach 10s")

    if not _FEED_MONITOR_STARTED:
        monitor_feed(symbol, interval)


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
    logging.info("Candle-WebSocket gestoppt")



def _monitor_loop(symbol: str, interval: str) -> None:
    """Background watchdog checking for stalled candle feed."""
    global _FEED_MONITOR_STARTED
    last_ok: bool | None = None
    while _FEED_MONITOR_STARTED:
        try:
            import global_state

            last_ts = global_state.last_feed_time
            alive = last_ts is not None and time.time() - last_ts <= 30
            if not alive:
                if last_ok is not False:
                    logging.warning("Feed tot – versuche Neustart")
                stop_candle_websocket()
                start_candle_websocket(symbol, interval)
                last_ok = False
            else:
                if last_ok is not True:
                    logging.info("Candle-Feed aktiv")
                last_ok = True
        except Exception as exc:
            logging.error("Feed-Monitor Fehler: %s", exc)
        time.sleep(20)


def monitor_feed(symbol: str, interval: str) -> None:
    """Start feed monitor thread once."""
    global _FEED_MONITOR_STARTED, _FEED_MONITOR_THREAD
    if _FEED_MONITOR_STARTED:
        return
    logging.info("Candle-Feed Monitor gestartet")
    _FEED_MONITOR_STARTED = True
    _FEED_MONITOR_THREAD = threading.Thread(target=_monitor_loop, args=(symbol, interval), daemon=True)
    _FEED_MONITOR_THREAD.start()


def is_websocket_running() -> bool:
    """Return ``True`` if the websocket manager is active."""
    return WebSocketStatus.is_running()


def get_last_candle_time() -> Optional[float]:
    """Return the timestamp of the most recent closed candle."""
    return binance_ws.last_candle_time



def _fetch_ws_price(symbol: str) -> Optional[float]:
    """Return latest price from websocket if available."""
    if not _WS_STARTED:
        start_websocket(symbol)
    price = _WS_PRICE.get(symbol)
    WebSocketStatus.set_running(price is not None)
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
    global _WS_CANDLES
    _WS_CANDLES.append(candle)
    if len(_WS_CANDLES) > 1000:
        _WS_CANDLES.pop(0)
    WebSocketStatus.set_running(True)
    logging.debug("Candle gespeichert: %s", candle)
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
    """Convenience helper returning only the latest candle.

    Checks that the returned candle contains complete OHLCV data. If the
    candle is incomplete, ``None`` is returned and a warning is logged.
    """
    candles = get_latest_candle_batch(symbol, interval, 1)
    candle = candles[-1] if candles else None
    if candle and not all(
        k in candle and candle[k] is not None for k in ("open", "high", "low", "close", "volume")
    ):
        logging.warning("fetch_latest_candle: incomplete data %s", candle)
        return None
    return candle
