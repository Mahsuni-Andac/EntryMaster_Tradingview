import unittest
from andac_entry_master import AndacEntryMaster
from entry_logic import should_enter

class EntryLogicTest(unittest.TestCase):
    def test_entry_signal_rsi_engulfing(self):
        indicator = AndacEntryMaster(lookback=1, puffer=1, opt_engulf=True)
        # history candles
        indicator.evaluate({"open":100, "high":110, "low":90, "close":95, "volume":1000})
        indicator.evaluate({"open":108, "high":109, "low":101, "close":102, "volume":1200})
        candle = {"open":100, "high":112, "low":98, "close":110, "volume":9000}
        signal = should_enter(candle, indicator)
        self.assertEqual(signal.signal, "long")

if __name__ == '__main__':
    unittest.main()
