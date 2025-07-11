import os
import unittest
from dydx_trader import is_dydx_configured


class DydxConfigTest(unittest.TestCase):
    def test_env_detection(self):
        os.environ['DYDX_PRIVATE_KEY'] = 'x'
        self.assertTrue(is_dydx_configured({}))
        del os.environ['DYDX_PRIVATE_KEY']

    def test_settings_detection(self):
        self.assertTrue(is_dydx_configured({'dydx_private_key': 'x'}))
        self.assertFalse(is_dydx_configured({}))


if __name__ == '__main__':
    unittest.main()

