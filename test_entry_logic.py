import unittest
from entry_logic import should_enter

class EntryLogicTest(unittest.TestCase):
    def test_entry_signal_rsi_engulfing(self):
        indicator = {
            "rsi": 55,
            "atr": 2,
            "avg_volume": 1100,
            "high_lookback": 110,
            "low_lookback": 90,
            "prev_close": 102,
            "prev_open": 108,
            "mtf_ok": True,
            "prev_bull_signal": False,
            "prev_baer_signal": False,
        }
        config = {
            "lookback": 1,
            "puffer": 1,
            "volumen_factor": 1.2,
            "opt_engulf": True,
            "opt_engulf_bruch": False,
            "opt_engulf_big": False,
            "opt_confirm_delay": False,
            "opt_mtf_confirm": False,
            "opt_volumen_strong": False,
            "opt_safe_mode": False,
            "opt_rsi_ema": False,
        }
        candle = {"open":100, "high":112, "low":98, "close":110, "volume":9000}
        signal = should_enter(candle, indicator, config)
        self.assertEqual(signal.signal, "long")

if __name__ == '__main__':
    unittest.main()
