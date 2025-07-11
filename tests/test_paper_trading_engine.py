import unittest
from paper_trading.engine import PaperTradingEngine

class PaperTradingEngineTest(unittest.TestCase):
    def test_open_and_close(self):
        engine = PaperTradingEngine(balance=1000, use_slippage=False)
        engine._order_book = lambda: (100.0, 101.0)
        engine.get_funding_rate = lambda: 0.0
        engine.open_position('long', amount=10, sl=90, tp=110)
        self.assertIsNotNone(engine.position)
        engine.close_position('test')
        self.assertIsNone(engine.position)
        self.assertEqual(len(engine.trade_log), 2)

    def test_pnl_calculation(self):
        pnl = PaperTradingEngine.calculate_pnl(100, 101, leverage=5, margin=100, side='long')
        self.assertAlmostEqual(pnl, 5.0, places=2)

    def test_partial_close(self):
        engine = PaperTradingEngine(balance=1000, leverage=10, use_slippage=False)
        engine._order_book = lambda: (100.0, 101.0)
        engine.get_funding_rate = lambda: 0.0
        engine.open_position('long', amount=100, sl=90, tp=110)

        self.assertIsNotNone(engine.position)

        entry_price = 101.0 * 1.0002
        total_size = 100 * 10 / entry_price
        entry_fee = entry_price * total_size * engine.fee_rate
        balance_after_open = 1000 - entry_fee

        engine.partial_close(50)

        exit_price = 100.0 * 0.9998
        size_closed = 50 * 10 / entry_price
        gross = PaperTradingEngine.calculate_pnl(entry_price, exit_price, 10, 50, 'long')
        fee_close = exit_price * size_closed * engine.fee_rate
        realized = gross - fee_close
        expected_balance = balance_after_open + realized

        self.assertAlmostEqual(engine.balance, expected_balance, places=2)
        self.assertIsNotNone(engine.position)
        self.assertAlmostEqual(engine.position.margin, 50, places=2)
        self.assertAlmostEqual(engine.position.size, total_size - size_closed, places=4)

    def test_partial_close_quarter(self):
        """25% der Position schließen und nur diesen Anteil verbuchen."""
        engine = PaperTradingEngine(balance=1000, leverage=10, use_slippage=False)
        engine._order_book = lambda: (100.0, 101.0)
        engine.get_funding_rate = lambda: 0.0

        engine.open_position('long', amount=100, sl=90, tp=110)

        entry_price = 101.0 * 1.0002
        total_size = 100 * 10 / entry_price
        entry_fee = entry_price * total_size * engine.fee_rate
        balance_after_open = 1000 - entry_fee

        engine.partial_close(25)

        exit_price = 100.0 * 0.9998
        size_closed = 25 * 10 / entry_price
        gross = PaperTradingEngine.calculate_pnl(entry_price, exit_price, 10, 25, 'long')
        fee_close = exit_price * size_closed * engine.fee_rate
        realized = gross - fee_close
        expected_balance = balance_after_open + realized

        self.assertAlmostEqual(engine.balance, expected_balance, places=2)
        self.assertIsNotNone(engine.position)
        self.assertAlmostEqual(engine.position.margin, 75, places=2)
        self.assertAlmostEqual(engine.position.size, total_size - size_closed, places=4)

if __name__ == '__main__':
    unittest.main()
