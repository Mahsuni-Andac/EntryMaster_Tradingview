# data_provider.py

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
_WS_CANDLES: list[Candle] = []
_CANDLE_LOCK = threading.Lock()
_MAX_CANDLES = 1000
_WS_STARTED: bool = False
_CANDLE_WS_STARTED: bool = False
_FEED_MONITOR_THREAD: threading.Thread | None = None
_FEED_MONITOR_STARTED: bool = False
_FEED_CHECK_INTERVAL = 20
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

    if _WS_STARTED and _WS_CLIENT and _WS_CLIENT.thread and _WS_CLIENT.thread.is_alive():
        return
    if _WS_STARTED:
        logger.info("Price WebSocket neu gestartet")
        _WS_STARTED = False

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
        except Exception as exc:
            logger.error("WebSocket Fehler: %s", exc)

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

    if (
        _CANDLE_WS_STARTED
        and _CANDLE_WS_CLIENT
        and _CANDLE_WS_CLIENT.thread
        and _CANDLE_WS_CLIENT.thread.is_alive()
    ):
        logger.debug("Candle-WebSocket bereits aktiv")
        return

    logger.info("WebSocket Candle-Stream gestartet")
    _CANDLE_WS_CLIENT = binance_ws.BinanceCandleWebSocket(
        update_candle_feed, symbol=symbol, interval=interval
    )
    _CANDLE_WS_CLIENT.start()
    _CANDLE_WS_STARTED = True

    start_time = time.time()
    error_logged = False
    while time.time() - start_time < 10:
        with _CANDLE_LOCK:
            has_candles = bool(_WS_CANDLES)
        if has_candles:
            logger.info("Erste Candle(s) empfangen – WebSocket läuft stabil")
            break
        if not error_logged and time.time() - start_time >= 5:
            logger.warning("FEED ERROR: Keine Candle-Daten empfangen nach 5s")
            error_logged = True
        time.sleep(0.5)
    else:
        logger.warning(
            "Kein Candle-Update nach 10s – prüfen, ob Binance-Daten verfügbar sind"
        )

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
    logger.info("Candle-WebSocket gestoppt")

_FEED_STUCK_COUNT = 0
_FEED_LAST_LEN = 0


def _monitor_loop(symbol: str, interval: str) -> None:
    global _FEED_MONITOR_STARTED, _FEED_STUCK_COUNT, _FEED_LAST_LEN

    while _FEED_MONITOR_STARTED:
        time.sleep(_FEED_CHECK_INTERVAL)
        try:
            import global_state

            last_ts = global_state.last_feed_time
            last_candle_time = get_last_candle_time()

            alive = (
                last_ts is not None
                and time.time() - last_ts <= 30
                and last_candle_time is not None
                and time.time() - last_candle_time <= 65
            )

            current_len = len(_WS_CANDLES)
            stuck = current_len == _FEED_LAST_LEN
            _FEED_LAST_LEN = current_len

            if not alive or stuck:
                logger.warning(
                    "FEED ERROR: Candle-Feed steht (len=%s)", current_len
                )
                _FEED_STUCK_COUNT += 1
                if _FEED_STUCK_COUNT >= 2:
                    stop_candle_websocket()
                    start_candle_websocket(symbol, interval)
                    _FEED_STUCK_COUNT = 0
            else:
                logger.debug("Candle-Feed aktiv (%s Candles)", current_len)
                _FEED_STUCK_COUNT = 0
        except Exception as exc:
            logger.error("Feed-Monitor Fehler: %s", exc)

def monitor_feed(symbol: str, interval: str) -> None:
    global _FEED_MONITOR_STARTED, _FEED_MONITOR_THREAD
    if _FEED_MONITOR_STARTED and _FEED_MONITOR_THREAD and _FEED_MONITOR_THREAD.is_alive():
        return

    logger.info("Candle-Feed Monitor gestartet")
    _FEED_MONITOR_STARTED = True
    _FEED_MONITOR_THREAD = threading.Thread(
        target=_monitor_loop, args=(symbol, interval), daemon=True
    )
    _FEED_MONITOR_THREAD.start()

def get_last_candle_time() -> Optional[float]:
    return binance_ws.last_candle_time

def _fetch_ws_price(symbol: str) -> Optional[float]:
    if not _WS_STARTED or not (_WS_CLIENT and _WS_CLIENT.thread and _WS_CLIENT.thread.is_alive()):
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

def is_candle_valid(candle: dict) -> bool:
    required = ("timestamp", "open", "high", "low", "close", "volume")
    return all(key in candle and candle[key] not in (None, "") for key in required)

def update_candle_feed(candle: Candle) -> None:
    if not is_candle_valid(candle):
        logger.warning("Ungültige Candle empfangen: %s", candle)
        return

    with _CANDLE_LOCK:
        _WS_CANDLES.append(candle)
        if len(_WS_CANDLES) > _MAX_CANDLES:
            _WS_CANDLES.pop(0)
        logger.debug("%d Candles im Feed", len(_WS_CANDLES))

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
    with _CANDLE_LOCK:
        return list(_WS_CANDLES[-limit:])

def fetch_latest_candle(symbol: str = "BTCUSDT", interval: str = "1m") -> Optional[Candle]:
    candles = get_latest_candle_batch(symbol, interval, 1)
    candle = candles[-1] if candles else None
    if candle and not is_candle_valid(candle):
        logger.warning("fetch_latest_candle: incomplete data %s", candle)
        return None
    return candle
