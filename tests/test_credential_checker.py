import unittest
from unittest.mock import patch, MagicMock
from ecdsa import SigningKey, SECP256k1

import credential_checker
from credential_checker import check_exchange_credentials


class CredentialCheckerTest(unittest.TestCase):
    @patch('dydx_api_utils.requests.get')
    def test_invalid_dydx_wallet(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        ok, msg = check_exchange_credentials('dYdX', wallet='abc', private_key='0x' + '1'*64)
        self.assertFalse(ok)
        self.assertIn('ungültig', msg.lower())

    @patch('dydx_api_utils.requests.get')
    def test_dydx_mismatch(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        ok, msg = check_exchange_credentials('dYdX', wallet='dydx1wrong', private_key='0x' + '1'*64)
        self.assertFalse(ok)

    @patch('dydx_api_utils.requests.get')
    def test_dydx_valid_pair(self, mock_get):
        sk = SigningKey.generate(curve=SECP256k1)
        priv = '0x' + sk.to_string().hex()
        wallet = credential_checker._derive_address(priv, 'dydx')
        mock_resp = MagicMock(status_code=200)
        mock_get.return_value = mock_resp
        ok, msg = check_exchange_credentials('dYdX', wallet=wallet, private_key=priv)
        self.assertTrue(ok)
        self.assertIn('dydx', msg.lower())

    @patch('mexc_api_utils.requests.get')
    def test_mexc_success(self, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {'success': True, 'data': {'foo': 'bar'}}
        mock_get.return_value = mock_resp
        ok, msg = check_exchange_credentials('MEXC', key='k' * 6, secret='s' * 6)
        self.assertTrue(ok)
        self.assertIn('mexc', msg.lower())

    @patch('credential_checker.requests.get')
    def test_bybit_testnet(self, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        ok, msg = check_exchange_credentials('Bybit', key='test123', secret='secret')
        self.assertTrue(ok)
        self.assertIn('Testnet', msg)

    @patch('credential_checker.requests.get')
    def test_bitmex_success(self, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_get.return_value = mock_resp
        ok, msg = check_exchange_credentials('BitMEX', key='abcd1', secret='xyzt1')
        self.assertTrue(ok)
        self.assertIn('BitMEX', msg)


if __name__ == '__main__':
    unittest.main()
