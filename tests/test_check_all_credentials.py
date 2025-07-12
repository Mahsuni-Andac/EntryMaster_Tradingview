import os
import unittest
from unittest.mock import patch, MagicMock

from credential_checker import check_all_credentials

class AllCredentialCheckTest(unittest.TestCase):
    @patch('credential_checker.requests.get')
    @patch('dydx_api_utils.requests.get')
    def test_no_credentials(self, mock_dydx, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        mock_dydx.return_value = mock_resp
        settings = {}
        res = check_all_credentials(settings)
        self.assertFalse(res['live'])

    @patch('credential_checker.requests.get')
    @patch('dydx_api_utils.requests.get')
    def test_with_env_credentials(self, mock_dydx, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        mock_dydx.return_value = mock_resp
        os.environ['MEXC_API_KEY'] = 'key12345'
        os.environ['MEXC_API_SECRET'] = 'sec12345'
        os.environ['BITMEX_API_KEY'] = 'key12345'
        os.environ['BITMEX_API_SECRET'] = 'secret123'
        settings = {}
        res = check_all_credentials(settings)
        self.assertIn('mexc', res['active'])
        self.assertIn('bitmex', res['active'])
        self.assertTrue(res['live'])
        del os.environ['MEXC_API_KEY']
        del os.environ['MEXC_API_SECRET']
        del os.environ['BITMEX_API_KEY']
        del os.environ['BITMEX_API_SECRET']

if __name__ == '__main__':
    unittest.main()
