import unittest
import tkinter as tk
from gui.trading_gui_core import TradingGUI
from api_key_manager import APICredentialManager

class SettingStatusTest(unittest.TestCase):
    def test_invalid_time_format(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tkinter not available")
        gui = TradingGUI(root, APICredentialManager())
        # access first time filter start var
        var = gui.time_filters[0][0]
        var.set("99:99")
        gui.update_setting_status("time_filter_1_start", var)
        text = gui.status_labels["time_filter_1_start"].cget("text")
        self.assertIn("Fehler", text)
        root.destroy()

if __name__ == '__main__':
    unittest.main()
