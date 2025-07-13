# binance_ws.py

from websocket import WebSocketApp
import threading
import json
import time
import logging
from typing import Callable, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BaseWebSocket:

    def __init__(self, url: str, on_message: Callable):
        self.url = url
        self.on_message = on_message
        self.ws: WebSocketApp | None = None
        self.thread: threading.Thread | None = None

    def _run(self) -> None:
        while True:
            try:
                self.ws = WebSocketApp(self.url, on_message=self.on_message)
                self.ws.run_forever()
            except Exception as e:
                logger.error("WebSocket Fehler: %s", e)
                time.sleep(5)

    def start(self) -> None:
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self) -> None:
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)


last_candle_time: float | None = None


class BinanceWebSocket(BaseWebSocket):
    def __init__(self, on_price: Callable[[str], None]):
        url = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
        super().__init__(url, self._on_message)
        self.on_price = on_price

    def _on_message(self, ws, message) -> None:
        try:
            data = json.loads(message)
            k = data.get("k")
            if k and k.get("x"):
                price = k.get("c")
                if price:
                    self.on_price(price)
        except Exception as e:
            logger.error("WebSocket Fehler: %s", e)


class BinanceCandleWebSocket(BaseWebSocket):

    def __init__(
        self,
        on_candle: Optional[Callable[[dict], None]] = None,
        symbol: str = "btcusdt",
        interval: str = "1m",
    ):
        self.on_candle = on_candle
        self.symbol = symbol.lower()
        self.interval = interval
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_{self.interval}"
        super().__init__(url, self._on_message)
        self._warning_printed = False

    def _run(self) -> None:
        while True:
            try:
                self.ws = WebSocketApp(
                    self.url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever(ping_interval=10, ping_timeout=5)
            except Exception as e:
                logger.error("WebSocket Fehler: %s", e)
                time.sleep(5)
            else:
                break

    def _on_message(self, ws, message):
        logging.debug("📥 Raw: %s", message)
        global last_candle_time
        try:
            data = json.loads(message)
            k = data.get("k")
            if not k:
                return

            try:
                import global_state
                global_state.last_feed_time = time.time()
            except Exception as e:
                logging.error("Fehler beim Setzen von last_feed_time: %s", e)

            if not k.get("x"):
                return

            candle_ts = k.get("t") // 1000
            now = int(datetime.now(tz=timezone.utc).timestamp())

            if now - candle_ts > 65:
                logger.warning(
                    "⚠️ Candle veraltet – empfangen: %s, jetzt: %s", candle_ts, now
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

            last_candle_time = time.time()

            logging.debug(
                "✅ Candle abgeschlossen: Open=%s, Close=%s, Vol=%s",
                candle["open"],
                candle["close"],
                candle["volume"],
            )

            if self.on_candle:
                try:
                    self.on_candle(candle)
                except Exception as exc:
                    if not self._warning_printed:
                        logger.warning("Fehler beim Weiterleiten der Candle: %s", exc)
                        self._warning_printed = True

            try:
                import global_state
                global_state.last_feed_time = time.time()
            except Exception as e:
                logger.error("Fehler beim Setzen von last_feed_time: %s", e)
        except Exception as e:
            if not self._warning_printed:
                logger.warning("Candle-Daten unvollständig oder fehlerhaft: %s", e)
                self._warning_printed = True

    def _on_error(self, ws, error):
        logger.error("Candle-WS Fehler: %s", error)

    def _on_close(self, ws, status_code, msg):
        logger.info("Candle-WS geschlossen: %s %s", status_code, msg)


    def _on_close(self, ws, status_code, msg):
        logger.info("Candle-WS geschlossen: %s %s", status_code, msg)
