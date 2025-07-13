import unittest
import tkinter as tk
from gui.api_credential_frame import APICredentialFrame
from api_key_manager import APICredentialManager

class GUICredentialFrameTest(unittest.TestCase):
    def test_active_exchange_selection(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tkinter not available")
        frame = APICredentialFrame(root, APICredentialManager())
        bitmex = frame.vars["BitMEX"]
        # no exchange selected by default
        self.assertEqual(bitmex["entry1"].cget("state"), "disabled")
        # switch to BitMEX
        frame.active_exchange.set("BitMEX")
        frame._on_select()
        self.assertEqual(bitmex["entry1"].cget("state"), "normal")
        root.destroy()

    def test_default_data_source(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tkinter not available")
        frame = APICredentialFrame(root, APICredentialManager())
        self.assertEqual(frame.data_source_mode.get(), "auto")
        root.destroy()

if __name__ == '__main__':
    unittest.main()
