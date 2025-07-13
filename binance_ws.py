from websocket import WebSocketApp
import threading
import json


class BinanceWebSocket:
    def __init__(self, on_price):
        self.on_price = on_price
        self.thread: threading.Thread | None = None
        self.ws: WebSocketApp | None = None

    def _start_socket(self):
        socket = "wss://stream.binance.com:9443/ws/btcusdt@trade"
        self.ws = WebSocketApp(socket, on_message=self._on_message)
        self.ws.run_forever()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            price = data.get("p")
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

    def __init__(self, on_candle):
        self.on_candle = on_candle
        self.thread: threading.Thread | None = None
        self.ws: WebSocketApp | None = None
        self._warning_printed = False

    def _start_socket(self):
        socket = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
        self.ws = WebSocketApp(socket, on_message=self._on_message)
        self.ws.run_forever()

    def _on_message(self, ws, message):
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
            self.on_candle(candle)
        except Exception as e:
            if not self._warning_printed:
                print("⚠️ Candle-Daten unvollständig oder fehlerhaft", e)
                self._warning_printed = True

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
