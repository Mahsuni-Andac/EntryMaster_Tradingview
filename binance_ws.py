from websocket import WebSocketApp
import threading
import json
import time
from typing import Callable

last_candle_time: float | None = None


class BinanceWebSocket:
    def __init__(self, on_price):
        self.on_price = on_price
        self.thread: threading.Thread | None = None
        self.ws: WebSocketApp | None = None

    def _start_socket(self):
        socket = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
        self.ws = WebSocketApp(socket, on_message=self._on_message)
        self.ws.run_forever()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            k = data.get("k")
            if k and k.get("x"):
                price = k.get("c")
                if price:
                    self.on_price(price)
        except Exception as e:
            print("WebSocket Fehler:", e)

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._start_socket, daemon=True)
        self.thread.start()

    def stop(self):
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)


class BinanceCandleWebSocket:
    """WebSocket manager for Binance candle streams."""

    def __init__(self, on_candle: Callable[[dict], None], symbol: str = "btcusdt", interval: str = "1m"):
        self.on_candle = on_candle
        self.symbol = symbol.lower()
        self.interval = interval
        self.thread: threading.Thread | None = None
        self.ws: WebSocketApp | None = None
        self._warning_printed = False

    def run(self) -> None:
        """Open the websocket and keep the connection alive."""
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_{self.interval}"
        while True:
            try:
                self.ws = WebSocketApp(
                    url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever(ping_interval=10, ping_timeout=5)
            except Exception as e:
                print("WebSocket Fehler:", e)
                time.sleep(5)
            else:
                break

    def _on_message(self, ws, message):
        """Handle incoming kline messages and forward completed candles."""
        print("\ud83d\udce5 Raw:", message)
        global last_candle_time
        try:
            data = json.loads(message)
            k = data.get("k")
            if not k or not k.get("x"):
                return

            candle = {
                "timestamp": k.get("t"),
                "open": float(k.get("o")),
                "high": float(k.get("h")),
                "low": float(k.get("l")),
                "close": float(k.get("c")),
                "volume": float(k.get("v")),
            }

            # keep internal timestamp for debug/analytics
            last_candle_time = time.time()

            print(
                f"✅ Candle abgeschlossen: Open={candle['open']}, Close={candle['close']}, Vol={candle['volume']}"
            )

            # push candle to data provider and update global feed timestamp
            try:
                from data_provider import update_candle_feed

                update_candle_feed(candle)
            except Exception as exc:  # pragma: no cover - runtime safety
                if not self._warning_printed:
                    print("⚠️ Fehler beim Weiterleiten der Candle", exc)
                    self._warning_printed = True

            try:
                import global_state

                global_state.last_feed_time = time.time()
            except Exception:
                pass

            if self.on_candle:
                # forward the candle to optional callback for further processing
                self.on_candle(candle)
        except Exception as e:
            if not self._warning_printed:
                print("⚠️ Candle-Daten unvollständig oder fehlerhaft", e)
                self._warning_printed = True

    def _on_error(self, ws, error):
        """Log websocket errors."""
        print("❌ Candle-WS Fehler:", error)

    def _on_close(self, ws, status_code, msg):
        """Log websocket close events."""
        print(f"🔌 Candle-WS geschlossen: {status_code} {msg}")

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
