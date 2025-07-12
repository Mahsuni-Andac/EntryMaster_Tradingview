import unittest
from system_monitor import SystemMonitor

class DummyGUI:
    def __init__(self):
        self.running = True
        self.feed_status = None

    def update_feed_status(self, ok: bool, reason=None) -> None:
        self.feed_status = ok

    def update_api_status(self, ok: bool, reason=None) -> None:
        pass

    def log_event(self, msg: str) -> None:
        pass

class SystemMonitorStateTest(unittest.TestCase):
    def test_pause_and_resume(self):
        gui = DummyGUI()
        mon = SystemMonitor(gui)
        # simulate feed loss
        mon._handle_feed_down("lost")
        self.assertFalse(gui.running)
        self.assertFalse(mon._feed_ok)
        self.assertEqual(gui.feed_status, False)
        # restore feed
        mon._handle_feed_up()
        self.assertTrue(gui.running)
        self.assertTrue(mon._feed_ok)
        self.assertEqual(gui.feed_status, True)

if __name__ == '__main__':
    unittest.main()
