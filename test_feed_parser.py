import unittest
import json
from datetime import datetime, timezone

from binance_ws import BinanceCandleWebSocket

class FeedParserTest(unittest.TestCase):
    def test_parse_ws_candle(self):
        ws = BinanceCandleWebSocket()
        result = []
        def _collect(c):
            result.append(c)
        ws.on_candle = _collect
        ts = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        msg = json.dumps({
            "k": {
                "t": ts,
                "x": True,
                "o": "10",
                "h": "12",
                "l": "9",
                "c": "11",
                "v": "100"
            }
        })
        ws._on_message(None, msg)
        self.assertEqual(len(result), 1)
        candle = result[0]
        self.assertEqual(candle["open"], 10.0)
        self.assertEqual(candle["close"], 11.0)
        self.assertEqual(candle["high"], 12.0)
        self.assertEqual(candle["low"], 9.0)
        self.assertEqual(candle["volume"], 100.0)

if __name__ == '__main__':
    unittest.main()
