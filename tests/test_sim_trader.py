import unittest
from sim_trader import SimTrader


class SimTraderTest(unittest.TestCase):
    def test_place_order_without_sl_tp(self):
        trader = SimTrader()
        result = trader.place_order(side="long", quantity=1.0, entry_price=100.0)
        self.assertTrue(result["success"])
        order = result["order"]
        self.assertIsNone(order["stop_loss"])
        self.assertIsNone(order["take_profit"])
        self.assertEqual(len(trader.orders), 1)


if __name__ == "__main__":
    unittest.main()
