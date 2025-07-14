# binance_ws.py

from websocket import WebSocketApp
import threading
import json
import time
import logging
from typing import Callable, Optional
from datetime import datetime, timezone
from config import BINANCE_SYMBOL, BINANCE_INTERVAL
from status_events import StatusDispatcher
import global_state
from config_manager import config

logger = logging.getLogger(__name__)


class BaseWebSocket:

    def __init__(self, url: str, on_message: Callable):
        self.url = url
        self.on_message = on_message
        self.ws: WebSocketApp | None = None
        self.thread: threading.Thread | None = None
        self._running = False

    def _run(self) -> None:
        time.sleep(2)
        while self._running:
            try:
                self.ws = WebSocketApp(self.url, on_message=self.on_message)
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                logger.error("WebSocket Fehler: %s", e)
                time.sleep(5)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self) -> None:
        self._running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)


last_candle_time: float | None = None




class BinanceCandleWebSocket(BaseWebSocket):

    def __init__(
        self,
        on_candle: Optional[Callable[[dict], None]] = None,
    ):
        self.on_candle = on_candle
        self.symbol = BINANCE_SYMBOL.lower()
        self.interval = BINANCE_INTERVAL
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_{self.interval}"
        super().__init__(url, self._on_message)
        self._warning_printed = False
        self.backoff = [5, 10, 30]
        self.max_retries = int(config.get("ws_max_retries", 5))
        self._retry_count = 0

    def _run(self) -> None:
        time.sleep(2)
        interval_sec = 60
        try:
            interval_sec = int(self.interval.rstrip('m')) * 60
        except Exception:
            pass
        while self._running:
            try:
                StatusDispatcher.dispatch("feed", False, "🔄 Reconnect läuft…") if self._retry_count else None
                self.ws = WebSocketApp(
                    self.url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
                StatusDispatcher.dispatch("feed", True)
                self._retry_count = 0
            except Exception as e:
                logger.error("WebSocket Fehler: %s", e)
                self._retry_count += 1
            if not self._running:
                break
            if global_state.last_feed_time and time.time() - global_state.last_feed_time > interval_sec * 2:
                logger.warning("Feed zu alt, versuche Reconnect")
            delay = self.backoff[min(self._retry_count, len(self.backoff) - 1)]
            if self._retry_count >= self.max_retries:
                StatusDispatcher.dispatch("feed", False, "❌ Kein Feed")
                self._retry_count = 0
            time.sleep(delay)

    def _on_message(self, ws, message):
        global last_candle_time
        try:
            data = json.loads(message)
            k = data.get("k")
            if not k or not k.get("x"):
                return

            try:
                import global_state
                global_state.last_feed_time = time.time()
            except Exception as e:
                logging.error("Fehler beim Setzen von last_feed_time: %s", e)

            candle_ts = k.get("t") // 1000
            now = int(datetime.now(tz=timezone.utc).timestamp())

            if now - candle_ts > 90:
                logger.warning(
                    f"⚠️ Veraltete Candle empfangen: Zeitdifferenz = {now - candle_ts:.2f}s"
                )
                return

            candle = {
                "timestamp": candle_ts,
                "open": float(k.get("o")),
                "high": float(k.get("h")),
                "low": float(k.get("l")),
                "close": float(k.get("c")),
                "volume": float(k.get("v")),
            }

            logger.debug("Candle received: %s", candle)

            last_candle_time = time.time()

            if self.on_candle:
                try:
                    self.on_candle(candle)
                except Exception as exc:
                    if not self._warning_printed:
                        logger.warning("Fehler beim Weiterleiten der Candle: %s", exc)
                        self._warning_printed = True
        except Exception as e:
            if not self._warning_printed:
                logger.warning("Candle-Daten unvollständig oder fehlerhaft: %s", e)
                self._warning_printed = True

    def _on_error(self, ws, error):
        logger.error("Candle-WS Fehler: %s", error)

    def _on_close(self, ws, status_code, msg):
        logger.info("Candle-WS geschlossen: %s %s", status_code, msg)

    def _on_open(self, ws):
        logger.info("Binance WebSocket verbunden")
