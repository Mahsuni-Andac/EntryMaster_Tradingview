import unittest
from trade_executor import calculate_pnl
from config import SETTINGS

class CalculatePnlTest(unittest.TestCase):
    def test_leverage_pnl(self):
        original_leverage = SETTINGS.get("leverage", 1)
        SETTINGS["leverage"] = 5

        position = {
            "entry": 100.0,
            "size": 1.0,  # size does not matter as margin is derived
            "direction": "long",
            "margin": 100.0,  # eingesetztes Kapital
            "fee": 0.0,
        }
        # 1% Kursanstieg bei x5 Hebel => 5% Gewinn = 5 USD
        pnl = calculate_pnl(position, 101.0)
        self.assertAlmostEqual(pnl, 5.0, places=2)

        SETTINGS["leverage"] = original_leverage

if __name__ == '__main__':
    unittest.main()
