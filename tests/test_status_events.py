import unittest
from status_events import StatusDispatcher
from system_monitor import SystemMonitor

class DummyGUI:
    def __init__(self):
        self.running = True
    def update_feed_status(self, ok: bool, reason=None):
        pass
    def update_api_status(self, ok: bool, reason=None):
        pass
    def log_event(self, msg: str):
        pass

class DispatcherTest(unittest.TestCase):
    def test_feed_callbacks(self):
        gui = DummyGUI()
        mon = SystemMonitor(gui)
        events = []
        StatusDispatcher._subs['feed'].clear()
        StatusDispatcher.on_feed_status(lambda ok, r=None: events.append((ok, r)))
        mon._handle_feed_down('err')
        self.assertEqual(events[-1], (False, 'err'))
        mon._handle_feed_up()
        self.assertEqual(events[-1], (True, None))

if __name__ == '__main__':
    unittest.main()
