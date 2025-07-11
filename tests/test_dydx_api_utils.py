import unittest
from unittest.mock import patch, MagicMock

from dydx_api_utils import check_dydx_api


class DydxApiUtilTest(unittest.TestCase):
    @patch('dydx_api_utils.requests.get')
    def test_api_ok(self, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_get.return_value = mock_resp
        ok, msg = check_dydx_api()
        self.assertTrue(ok)
        self.assertIn('OK', msg)

    @patch('dydx_api_utils.requests.get')
    def test_api_error(self, mock_get):
        mock_resp = MagicMock(status_code=404, text='not found')
        mock_get.return_value = mock_resp
        ok, msg = check_dydx_api()
        self.assertFalse(ok)
        self.assertIn('404', msg)


if __name__ == '__main__':
    unittest.main()
