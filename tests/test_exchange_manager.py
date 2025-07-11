import os
import unittest
from exchange_manager import detect_available_exchanges

class ExchangeDetectTest(unittest.TestCase):
    def test_detect_mexc(self):
        os.environ['MEXC_API_KEY'] = 'k'
        os.environ['MEXC_API_SECRET'] = 's'
        res = detect_available_exchanges({})
        self.assertIn('mexc', res)
        del os.environ['MEXC_API_KEY']
        del os.environ['MEXC_API_SECRET']

    def test_detect_dydx_settings(self):
        res = detect_available_exchanges({'dydx_private_key': 'x'})
        self.assertIn('dydx', res)

    def test_detect_bitmex(self):
        os.environ['BITMEX_API_KEY'] = 'k'
        os.environ['BITMEX_API_SECRET'] = 's'
        res = detect_available_exchanges({})
        self.assertIn('bitmex', res)
        del os.environ['BITMEX_API_KEY']
        del os.environ['BITMEX_API_SECRET']

if __name__ == '__main__':
    unittest.main()
