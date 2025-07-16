import unittest
from andac_entry_master import should_enter, _MASTER

class EntryLogicTest(unittest.TestCase):
    def test_entry_signal_rsi_engulfing(self):
        global _MASTER
        _MASTER = None
        config = {
            "lookback": 1,
            "puffer": 1,
            "volumen_factor": 1.2,
            "opt_engulf": True,
        }

        filler = {"open":100, "high":100, "low":99, "close":100, "volume":1000}
        prev = {"open":108, "high":110, "low":90, "close":102, "volume":1000}
        should_enter(filler, {}, config)
        should_enter(prev, {}, config)
        candle = {"open":100, "high":112, "low":98, "close":110, "volume":2000}
        signal = should_enter(candle, {}, config)
        self.assertEqual(signal.signal, "long")

if __name__ == '__main__':
    unittest.main()
