from websocket import WebSocketApp
import threading
import json

class BinanceWebSocket:
    def __init__(self, on_price):
        self.on_price = on_price
        self.thread = threading.Thread(target=self._start_socket, daemon=True)

    def _start_socket(self):
        socket = "wss://stream.binance.com:9443/ws/btcusdt@trade"
        ws = WebSocketApp(socket, on_message=self._on_message)
        ws.run_forever()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            price = data.get("p")
            if price:
                self.on_price(price)
        except Exception as e:
            print("WebSocket Fehler:", e)

    def start(self):
        self.thread.start()
