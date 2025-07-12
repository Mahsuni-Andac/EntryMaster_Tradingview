import unittest
from symbol_utils import bitmex_symbol

class BitmexSymbolTest(unittest.TestCase):
    def test_btc_mapping(self):
        self.assertEqual(bitmex_symbol('BTCUSDT'), 'XBTUSD')
        self.assertEqual(bitmex_symbol('btc_usdt'), 'XBTUSD')

    def test_eth_mapping(self):
        self.assertEqual(bitmex_symbol('ETHUSDT'), 'ETHUSD')
        self.assertEqual(bitmex_symbol('eth/usdt'), 'ETHUSD')

    def test_unknown(self):
        self.assertEqual(bitmex_symbol('XRPUSDT'), 'XRPUSDT')

if __name__ == '__main__':
    unittest.main()
