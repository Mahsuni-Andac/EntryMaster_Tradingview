import os
import unittest
from unittest.mock import patch, MagicMock

from credential_checker import check_all_credentials

class AllCredentialCheckTest(unittest.TestCase):
    @patch('mexc_api_utils.requests.get')
    @patch('credential_checker.requests.get', return_value=MagicMock(status_code=200, text='OK'))
    @patch('dydx_api_utils.requests.get', return_value=MagicMock(status_code=200, text='OK'))
    def test_no_credentials(self, mock_dydx, mock_get, mock_mexc):
        mock_get.return_value.raise_for_status.return_value = None
        mock_mexc_resp = MagicMock()
        mock_mexc_resp.json.return_value = {'success': False}
        mock_mexc.return_value = mock_mexc_resp
        mock_dydx.return_value.raise_for_status.return_value = None
        settings = {}
        res = check_all_credentials(settings)
        self.assertFalse(res['live'])

    @patch('mexc_api_utils.requests.get')
    @patch('credential_checker.requests.get', return_value=MagicMock(status_code=200, text='OK'))
    @patch('dydx_api_utils.requests.get', return_value=MagicMock(status_code=200, text='OK'))
    def test_with_env_credentials(self, mock_dydx, mock_get, mock_mexc):
        mock_get.return_value.raise_for_status.return_value = None
        mock_mexc_resp = MagicMock()
        mock_mexc_resp.json.return_value = {'success': True, 'data': {'d': 1}}
        mock_mexc.return_value = mock_mexc_resp
        mock_dydx.return_value.raise_for_status.return_value = None
        os.environ['MEXC_API_KEY'] = 'key12345'
        os.environ['MEXC_API_SECRET'] = 'sec12345'
        settings = {}
        res = check_all_credentials(settings)
        self.assertIn('mexc', res['active'])
        self.assertTrue(res['live'])
        del os.environ['MEXC_API_KEY']
        del os.environ['MEXC_API_SECRET']

    @patch('mexc_api_utils.requests.get')
    @patch('credential_checker.requests.get', return_value=MagicMock(status_code=200, text='OK'))
    @patch('dydx_api_utils.requests.get', return_value=MagicMock(status_code=200, text='OK'))
    def test_enabled_filter(self, mock_dydx, mock_get, mock_mexc):
        mock_get.return_value.raise_for_status.return_value = None
        mock_mexc_resp = MagicMock()
        mock_mexc_resp.json.return_value = {'success': True, 'data': {'d': 1}}
        mock_mexc.return_value = mock_mexc_resp
        mock_dydx.return_value.raise_for_status.return_value = None
        os.environ['MEXC_API_KEY'] = 'key12345'
        os.environ['MEXC_API_SECRET'] = 'sec12345'
        res = check_all_credentials({}, enabled=['mexc'])
        self.assertIn('mexc', res['active'])
        self.assertNotIn('bitmex', res['active'])
        del os.environ['MEXC_API_KEY']
        del os.environ['MEXC_API_SECRET']

if __name__ == '__main__':
    unittest.main()
