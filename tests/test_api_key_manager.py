import os
import unittest
from api_key_manager import APICredentialManager

class CredentialManagerTest(unittest.TestCase):
    def test_set_and_clear(self):
        mgr = APICredentialManager()
        mgr.set_credentials('k', 's')
        self.assertEqual(mgr.get_key(), 'k')
        self.assertEqual(mgr.get_secret(), 's')
        mgr.clear()
        self.assertIsNone(mgr.get_key())
        self.assertIsNone(mgr.get_secret())

    def test_load_from_env(self):
        os.environ["MEXC_API_KEY"] = "env_key"
        os.environ["MEXC_API_SECRET"] = "env_secret"
        mgr = APICredentialManager()
        loaded = mgr.load_from_env()
        self.assertTrue(loaded)
        self.assertEqual(mgr.get_key(), "env_key")
        self.assertEqual(mgr.get_secret(), "env_secret")
        mgr.clear()
        del os.environ["MEXC_API_KEY"]
        del os.environ["MEXC_API_SECRET"]

if __name__ == '__main__':
    unittest.main()
