import unittest
from unittest.mock import MagicMock, patch

from data_provider import fetch_last_price

class BitmexPriceFeedTest(unittest.TestCase):
    @patch('data_provider._SESSION.get')
    def test_price_feed_mapping(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = [{"lastPrice": "123.45"}]
        mock_get.return_value = mock_resp

        price = fetch_last_price('bitmex', 'BTCUSDT')
        self.assertAlmostEqual(price, 123.45)
        called_url = mock_get.call_args[0][0]
        self.assertIn('symbol=XBTUSD', called_url)

if __name__ == '__main__':
    unittest.main()
