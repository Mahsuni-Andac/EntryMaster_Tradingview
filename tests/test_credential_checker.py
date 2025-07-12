import unittest
from unittest.mock import patch, MagicMock
from credential_checker import check_exchange_credentials

class CredentialCheckerTest(unittest.TestCase):
    @patch('credential_checker.requests.get')
    def test_bitmex_success(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        ok, msg = check_exchange_credentials('BitMEX', key='abcd1', secret='xyz12')
        self.assertTrue(ok)
        self.assertIn('BitMEX', msg)

if __name__ == '__main__':
    unittest.main()
