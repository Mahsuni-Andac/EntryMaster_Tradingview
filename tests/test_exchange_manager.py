import os
import unittest
from exchange_manager import detect_available_exchanges

class ExchangeDetectTest(unittest.TestCase):
    def test_detect_bitmex(self):
        os.environ['BITMEX_API_KEY'] = 'k'
        os.environ['BITMEX_API_SECRET'] = 's'
        res = detect_available_exchanges({})
        self.assertIn('bitmex', res)
        del os.environ['BITMEX_API_KEY']
        del os.environ['BITMEX_API_SECRET']

if __name__ == '__main__':
    unittest.main()
