# data_provider.py
#
# Changelog:
# - Fixed missing candle feed population by restoring internal update_candle_feed callback
# - Removed redundant logging and callback override
# - Simplified feed monitor logic

from __future__ import annotations

import logging
from typing import List, Optional, TypedDict
import time
import threading

import binance_ws
from tkinter import Tk, StringVar

logger = logging.getLogger(__name__)

_WS_CLIENT: binance_ws.BinanceWebSocket | None = None
_WS_PRICE: dict[str, float] = {}
_CANDLE_WS_CLIENT: binance_ws.BinanceCandleWebSocket | None = None
_WS_CANDLES: list["Candle"] = []
_WS_STARTED: bool = False
_CANDLE_WS_STARTED: bool = False
_FEED_MONITOR_THREAD: threading.Thread | None = None
_FEED_MONITOR_STARTED: bool = False
_TK_ROOT: Tk | None = None
price_var: StringVar | None = None

class WebSocketStatus:
    running = False

    @classmethod
    def is_running(cls) -> bool:
        return cls.running

    @classmethod
    def set_running(cls, value: bool) -> None:
        cls.running = value

def init_price_var(master: Tk) -> None:
    global price_var, _TK_ROOT
    _TK_ROOT = master
    if price_var is None:
        price_var = StringVar(master=master, value="--")

def start_websocket(symbol: str = "BTCUSDT") -> None:
    global _WS_STARTED, _WS_CLIENT
    if _WS_STARTED:
        return

    def handle(price: str) -> None:
        try:
            p = float(price)
            _WS_PRICE[symbol] = p
            WebSocketStatus.set_running(True)
            if price_var and _TK_ROOT:
                _TK_ROOT.after(0, lambda val=price: price_var.set(str(val)))
            try:
                import global_state
                global_state.last_feed_time = time.time()
            except Exception:
                pass
        except Exception as e:
            logger.error("WebSocket Fehler: %s", e)

    _WS_CLIENT = binance_ws.BinanceWebSocket(handle)
    _WS_CLIENT.start()
    _WS_STARTED = True
    logger.info("WebSocket verbunden: Binance BTCUSDT")

def stop_websocket() -> None:
    global _WS_CLIENT, _WS_STARTED
    if _WS_CLIENT:
        try:
            _WS_CLIENT.stop()
        except Exception:
            pass
    _WS_CLIENT = None
    _WS_STARTED = False
    WebSocketStatus.set_running(False)
    logger.info("WebSocket gestoppt")

def start_candle_websocket(symbol: str = "BTCUSDT", interval: str = "1m") -> None:
    global _CANDLE_WS_STARTED, _CANDLE_WS_CLIENT
    if _CANDLE_WS_STARTED:
        logger.warning("Candle-WebSocket bereits gestartet.")
        return

    logger.info("WebSocket Candle-Stream gestartet")
    _CANDLE_WS_CLIENT = binance_ws.BinanceCandleWebSocket(None, symbol=symbol, interval=interval)
    _CANDLE_WS_CLIENT.start()
    _CANDLE_WS_STARTED = True

    start_time = time.time()
    while time.time() - start_time < 10:
        if _WS_CANDLES:
            logger.info("Erste Candle(s) empfangen – WebSocket läuft stabil")
            break
        time.sleep(0.5)
    else:
        logger.warning("Kein Candle-Update nach 10s")

    if not _FEED_MONITOR_STARTED:
        monitor_feed(symbol, interval)

def stop_candle_websocket() -> None:
    global _CANDLE_WS_CLIENT, _CANDLE_WS_STARTED
    if _CANDLE_WS_CLIENT:
        try:
            _CANDLE_WS_CLIENT.stop()
        except Exception:
            pass
    _CANDLE_WS_CLIENT = None
    _CANDLE_WS_STARTED = False

def _monitor_loop(symbol: str, interval: str) -> None:
    global _FEED_MONITOR_STARTED
    last_ok: bool | None = None
    while _FEED_MONITOR_STARTED:
        try:
            import global_state
            last_ts = global_state.last_feed_time
            alive = last_ts is not None and time.time() - last_ts <= 30
            if not alive:
                if last_ok is not False:
                    logger.warning("Feed tot – versuche Neustart")
                stop_candle_websocket()
                start_candle_websocket(symbol, interval)
                last_ok = False
            else:
                if last_ok is not True:
                    logger.info("Candle-Feed aktiv")
                last_ok = True
        except Exception as exc:
            logger.error("Feed-Monitor Fehler: %s", exc)
        time.sleep(20)

def monitor_feed(symbol: str, interval: str) -> None:
    global _FEED_MONITOR_STARTED, _FEED_MONITOR_THREAD
    if _FEED_MONITOR_STARTED:
        return
    logger.info("Candle-Feed Monitor gestartet")
    _FEED_MONITOR_STARTED = True
    _FEED_MONITOR_THREAD = threading.Thread(target=_monitor_loop, args=(symbol, interval), daemon=True)
    _FEED_MONITOR_THREAD.start()

def websocket_active() -> bool:
    return WebSocketStatus.is_running()

def get_last_candle_time() -> Optional[float]:
    return binance_ws.last_candle_time

def _fetch_ws_price(symbol: str) -> Optional[float]:
    if not _WS_STARTED:
        start_websocket(symbol)
    price = _WS_PRICE.get(symbol)
    WebSocketStatus.set_running(price is not None)
    return price

def _normalize_symbol(symbol: str) -> str:
    return symbol.replace("/", "").replace("_", "").upper()

class Candle(TypedDict):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

def update_candle_feed(candle: Candle) -> None:
    global _WS_CANDLES
    _WS_CANDLES.append(candle)
    if len(_WS_CANDLES) > 1000:
        _WS_CANDLES.pop(0)
    WebSocketStatus.set_running(True)
    try:
        import global_state
        global_state.last_feed_time = time.time()
    except Exception:
        pass

def fetch_last_price(exchange: str = "binance", symbol: Optional[str] = None) -> Optional[float]:
    if exchange.lower() != "binance":
        logger.debug("Ignoring price request for unsupported exchange %s", exchange)
        return None
    pair = _normalize_symbol(symbol or "BTCUSDT")
    return _fetch_ws_price(pair)

def get_latest_candle_batch(symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 100) -> List[Candle]:
    return get_live_candles(symbol, interval, limit)

def get_live_candles(symbol: str, interval: str, limit: int) -> List[Candle]:
    if not _CANDLE_WS_STARTED:
        start_candle_websocket(symbol, interval)
    return _WS_CANDLES[-limit:]

def fetch_latest_candle(symbol: str = "BTCUSDT", interval: str = "1m") -> Optional[Candle]:
    candles = get_latest_candle_batch(symbol, interval, 1)
    candle = candles[-1] if candles else None
    if candle and not all(k in candle and candle[k] is not None for k in ("open", "high", "low", "close", "volume")):
        logger.warning("fetch_latest_candle: incomplete data %s", candle)
        return None
    return candle
