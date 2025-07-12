import unittest
import tkinter as tk
from gui.api_credential_frame import APICredentialFrame
from api_key_manager import APICredentialManager

class GUICredentialFrameTest(unittest.TestCase):
    def test_checkbox_enables_fields(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tkinter not available")
        frame = APICredentialFrame(root, APICredentialManager())
        data = frame.vars["MEXC"]
        self.assertEqual(data["entry1"].cget("state"), "disabled")
        data["enabled"].set(True)
        frame._toggle_exchange("MEXC")
        self.assertEqual(data["entry1"].cget("state"), "normal")
        data["enabled"].set(False)
        frame._toggle_exchange("MEXC")
        self.assertEqual(data["entry1"].cget("state"), "disabled")
        root.destroy()

if __name__ == '__main__':
    unittest.main()
