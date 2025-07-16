import unittest
import json
from datetime import datetime, timezone

from andac_entry_master import BinanceCandleWebSocket

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

    def test_ws_deduplication(self):
        import global_state
        global_state.reset_global_state()
        ws = BinanceCandleWebSocket()
        collected = []
        ws.on_candle = collected.append
        ts = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        msg = json.dumps({
            "k": {
                "t": ts,
                "x": True,
                "o": "1",
                "h": "1",
                "l": "1",
                "c": "1",
                "v": "1",
            }
        })
        ws._on_message(None, msg)
        ws._on_message(None, msg)  # duplicate
        self.assertEqual(len(collected), 1)

if __name__ == '__main__':
    unittest.main()
