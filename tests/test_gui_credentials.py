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
        mexc = frame.vars["MEXC"]
        dydx = frame.vars["dYdX"]
        # no exchange selected by default
        self.assertEqual(mexc["entry1"].cget("state"), "disabled")
        self.assertEqual(dydx["entry1"].cget("state"), "disabled")
        # switch to dYdX
        frame.active_exchange.set("dYdX")
        frame._on_select()
        self.assertEqual(dydx["entry1"].cget("state"), "normal")
        self.assertEqual(mexc["entry1"].cget("state"), "disabled")
        root.destroy()

if __name__ == '__main__':
    unittest.main()
