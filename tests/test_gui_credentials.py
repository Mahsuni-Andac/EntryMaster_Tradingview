import os
import unittest
import tkinter as tk
from gui.api_credential_frame import APICredentialFrame
from api_key_manager import APICredentialManager

class GUICredentialFrameTest(unittest.TestCase):
    def test_field_switch(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tkinter not available")
        frame = APICredentialFrame(root, APICredentialManager())
        frame.exchange_var.set('dYdX')
        frame._on_exchange_change()
        self.assertTrue(frame.wallet_entry.winfo_ismapped())
        frame.exchange_var.set('MEXC')
        frame._on_exchange_change()
        self.assertTrue(frame.key_entry.winfo_ismapped())
        root.destroy()

if __name__ == '__main__':
    unittest.main()
