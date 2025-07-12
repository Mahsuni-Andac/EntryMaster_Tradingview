import unittest
from unittest.mock import MagicMock, patch

from data_provider import fetch_last_price

class MexcPriceFeedTest(unittest.TestCase):
    @patch('data_provider._SESSION.get')
    def test_price_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'success': True, 'data': {'lastPrice': '99.9'}}
        mock_get.return_value = mock_resp

        price = fetch_last_price('mexc', 'BTC_USDT')
        self.assertAlmostEqual(price, 99.9)
        called_url = mock_get.call_args[0][0]
        self.assertIn('symbol=BTC_USDT', called_url)

    @patch('data_provider.logging.error')
    @patch('data_provider._SESSION.get')
    def test_symbol_error(self, mock_get, mock_log):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'success': False, 'code': 404, 'message': '合约不存在!'}
        mock_get.return_value = mock_resp

        price = fetch_last_price('mexc', 'FOO_USDT')
        self.assertIsNone(price)
        mock_log.assert_called()

if __name__ == '__main__':
    unittest.main()
