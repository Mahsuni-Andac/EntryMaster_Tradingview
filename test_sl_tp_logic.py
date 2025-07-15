import unittest
from adaptive_sl_manager import AdaptiveSLManager

class SLTPLogicTest(unittest.TestCase):
    def test_adaptive_sl_tp_long(self):
        manager = AdaptiveSLManager()
        candles = [
            {"high": 105, "low": 95, "close": 100},
        ] * 15
        sl, tp = manager.get_adaptive_sl_tp("long", 100, candles)
        self.assertLess(sl, 100)
        self.assertGreater(tp, 100)

    def test_calculate_atr_invalid(self):
        manager = AdaptiveSLManager()
        candles = [{"high": 1, "low": 1, "close": 1}] * 15
        with self.assertRaises(ValueError):
            manager.calculate_atr(candles)

if __name__ == "__main__":
    unittest.main()
