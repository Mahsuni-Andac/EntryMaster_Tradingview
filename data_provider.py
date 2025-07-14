# data_provider.py

from __future__ import annotations

import logging
from typing import List, Optional, TypedDict
import time
import threading
import queue

import binance_ws
from tkinter import Tk, StringVar
from config import BINANCE_SYMBOL, BINANCE_INTERVAL
import requests
from status_events import StatusDispatcher
from config_manager import config

logger = logging.getLogger(__name__)

_CANDLE_WS_CLIENT: binance_ws.BinanceCandleWebSocket | None = None
_WS_CANDLES: list[Candle] = []
_CANDLE_LOCK = threading.Lock()
_CANDLE_QUEUE: queue.Queue[Candle] = queue.Queue(maxsize=100)
_MAX_CANDLES = 1000
_CANDLE_WS_STARTED: bool = False
_FEED_MONITOR_THREAD: threading.Thread | None = None
_FEED_MONITOR_STARTED: bool = False
_FEED_CHECK_INTERVAL = 20
_TK_ROOT: Tk | None = None
price_var: StringVar | None = None
_DEFAULT_INTERVAL = BINANCE_INTERVAL


def _interval_to_seconds(interval: str) -> int:
    """Convert timeframe string like '1m' or '5h' to seconds."""
    try:
        if interval.endswith('m'):
            return int(interval[:-1]) * 60
        if interval.endswith('h'):
            return int(interval[:-1]) * 3600
        if interval.endswith('d'):
            return int(interval[:-1]) * 86400
    except Exception:
        pass
    return 60

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


def _fetch_rest_candles(interval: str, limit: int = 14) -> list["Candle"]:
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={BINANCE_SYMBOL}"
        f"&interval={interval}&limit={limit}"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    candles: list[Candle] = []
    for row in data:
        candles.append(
            {
                "timestamp": int(row[0] // 1000),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    return candles


def _load_initial_candles(interval: str, limit: int = 14) -> bool:
    StatusDispatcher.dispatch("feed", False, "REST-API-Call-14")
    try:
        candles = _fetch_rest_candles(interval, limit)
    except Exception as exc:
        logger.error("REST Candle Fetch failed: %s", exc)
        return False
    with _CANDLE_LOCK:
        _WS_CANDLES.extend(candles)
        if len(_WS_CANDLES) > _MAX_CANDLES:
            del _WS_CANDLES[:-_MAX_CANDLES]
    for candle in candles:
        try:
            _CANDLE_QUEUE.put_nowait(candle)
        except queue.Full:
            pass
    return True

def start_candle_websocket(interval: str | None = None) -> None:
    global _CANDLE_WS_STARTED, _CANDLE_WS_CLIENT, _DEFAULT_INTERVAL

    if interval:
        _DEFAULT_INTERVAL = interval
    else:
        interval = _DEFAULT_INTERVAL

    if (
        _CANDLE_WS_STARTED
        and _CANDLE_WS_CLIENT
        and _CANDLE_WS_CLIENT.thread
        and _CANDLE_WS_CLIENT.thread.is_alive()
    ):
        logger.debug("Candle-WebSocket bereits aktiv")
        return
    if _CANDLE_WS_STARTED:
        stop_candle_websocket()
        logger.info("Candle-WebSocket neu gestartet")

    if not _load_initial_candles(interval, 14):
        raise RuntimeError("Initial candle download failed")

    logger.info("WebSocket Candle-Stream gestartet")
    _CANDLE_WS_CLIENT = binance_ws.BinanceCandleWebSocket(
        update_candle_feed,
        interval=interval,
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
        monitor_feed()

def stop_candle_websocket() -> None:
    global _CANDLE_WS_CLIENT, _CANDLE_WS_STARTED
    if _CANDLE_WS_CLIENT:
        try:
            _CANDLE_WS_CLIENT.stop()
        except Exception:
            pass
    _CANDLE_WS_CLIENT = None
    _CANDLE_WS_STARTED = False
    stop_feed_monitor()
    logger.info("Candle-WebSocket gestoppt")

_FEED_STUCK_COUNT = 0
_FEED_LAST_LEN = 0
_LAST_LEN_CHANGE_TS: float | None = None
_MONITOR_START_TS: float | None = None


def _monitor_loop() -> None:
    global _FEED_MONITOR_STARTED, _FEED_STUCK_COUNT, _FEED_LAST_LEN, _LAST_LEN_CHANGE_TS

    timeframe_sec = _interval_to_seconds(_DEFAULT_INTERVAL)
    start_ts = _MONITOR_START_TS or time.time()

    while _FEED_MONITOR_STARTED:
        time.sleep(_FEED_CHECK_INTERVAL)
        try:
            import global_state

            last_ts = global_state.last_feed_time
            last_candle_time = get_last_candle_time()

            with _CANDLE_LOCK:
                current_len = len(_WS_CANDLES)

            if current_len != _FEED_LAST_LEN:
                _FEED_LAST_LEN = current_len

            last_update = _LAST_LEN_CHANGE_TS or start_ts
            if last_candle_time:
                last_update = max(last_update, last_candle_time)

            diff = time.time() - last_update

            if diff > timeframe_sec * 2:
                logger.warning(
                    "❌ Keine neue Candle seit %.0fs bei %s-Intervall – FEED ERROR",
                    diff,
                    _DEFAULT_INTERVAL,
                )
                _FEED_STUCK_COUNT += 1
                if _FEED_STUCK_COUNT >= 2:
                    stop_candle_websocket()
                    if not _CANDLE_WS_STARTED:
                        start_candle_websocket()
                    _FEED_STUCK_COUNT = 0
            else:
                logger.info("🕒 Letzte Candle vor %.0fs – alles OK", diff)
                _FEED_STUCK_COUNT = 0
        except Exception as exc:
            logger.error("Feed-Monitor Fehler: %s", exc)

def monitor_feed() -> None:
    global _FEED_MONITOR_STARTED, _FEED_MONITOR_THREAD, _MONITOR_START_TS, _FEED_LAST_LEN, _LAST_LEN_CHANGE_TS
    if _FEED_MONITOR_STARTED and _FEED_MONITOR_THREAD and _FEED_MONITOR_THREAD.is_alive():
        return

    logger.info("Candle-Feed Monitor gestartet")
    _FEED_MONITOR_STARTED = True
    _MONITOR_START_TS = time.time()
    with _CANDLE_LOCK:
        _FEED_LAST_LEN = len(_WS_CANDLES)
    _LAST_LEN_CHANGE_TS = None
    _FEED_MONITOR_THREAD = threading.Thread(
        target=_monitor_loop, daemon=True
    )
    _FEED_MONITOR_THREAD.start()

def stop_feed_monitor() -> None:
    global _FEED_MONITOR_STARTED, _FEED_MONITOR_THREAD
    if _FEED_MONITOR_STARTED:
        _FEED_MONITOR_STARTED = False
        if _FEED_MONITOR_THREAD and _FEED_MONITOR_THREAD.is_alive():
            _FEED_MONITOR_THREAD.join(timeout=1)
        _FEED_MONITOR_THREAD = None

def get_last_candle_time() -> Optional[float]:
    return binance_ws.last_candle_time



class Candle(TypedDict):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

def is_candle_valid(candle: dict) -> bool:
    required = ("timestamp", "close")
    return all(key in candle and candle[key] not in (None, "") for key in required)

def update_candle_feed(candle: Candle) -> None:
    logger.debug("update_candle_feed called: %s", candle)
    if not is_candle_valid(candle):
        logger.warning("Ungültige Candle empfangen: %s", candle)
        return

    global _LAST_LEN_CHANGE_TS, _FEED_LAST_LEN
    with _CANDLE_LOCK:
        _WS_CANDLES.append(candle)
        if len(_WS_CANDLES) > _MAX_CANDLES:
            _WS_CANDLES.pop(0)
        _FEED_LAST_LEN = len(_WS_CANDLES)
        _LAST_LEN_CHANGE_TS = time.time()
    try:
        _CANDLE_QUEUE.put_nowait(candle)
    except queue.Full:
        logger.warning("⚠️ Feed überlastet – Candles könnten verloren gehen")

    if price_var and _TK_ROOT:
        try:
            _TK_ROOT.after(0, lambda val=candle["close"]: price_var.set(str(val)))
        except Exception:
            pass

    WebSocketStatus.set_running(True)

def get_candle_queue() -> queue.Queue[Candle]:
    """Return the queue containing live candles."""
    return _CANDLE_QUEUE

def fetch_last_price() -> Optional[float]:
    candle = fetch_latest_candle()
    if candle:
        return candle.get("close")
    return None

def get_latest_candle_batch(limit: int = 100) -> List[Candle]:
    return get_live_candles(limit)

def get_live_candles(limit: int) -> List[Candle]:
    if not _CANDLE_WS_STARTED:
        start_candle_websocket()
    with _CANDLE_LOCK:
        return list(_WS_CANDLES[-limit:])

def fetch_latest_candle() -> Optional[Candle]:
    candles = get_latest_candle_batch(1)
    candle = candles[-1] if candles else None
    if candle and not is_candle_valid(candle):
        logger.warning("fetch_latest_candle: incomplete data %s", candle)
        return None
    return candle
