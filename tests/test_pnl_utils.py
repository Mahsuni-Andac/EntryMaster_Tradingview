import unittest
from pnl_utils import calculate_futures_pnl

class PnlUtilsTest(unittest.TestCase):
    def test_example(self):
        pnl = calculate_futures_pnl(100, 100.2, leverage=20, amount=1000, side='long')
        self.assertAlmostEqual(pnl, 40.0, places=2)

if __name__ == '__main__':
    unittest.main()
