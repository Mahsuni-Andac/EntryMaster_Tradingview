from config import SETTINGS

class GUIBridge:
    """Minimal helper to access GUI variables safely."""
    def __init__(self, gui_instance=None):
        self.gui = gui_instance

    @property
    def multiplier(self):
        if self.gui and hasattr(self.gui, "multiplier_entry"):
            try:
                return float(self.gui.multiplier_entry.get())
            except Exception:
                return SETTINGS.get("multiplier", 20)
        return SETTINGS.get("multiplier", 20)

    @property
    def auto_multiplier(self):
        if self.gui and hasattr(self.gui, "auto_multiplier"):
            try:
                return bool(self.gui.auto_multiplier.get())
            except Exception:
                return SETTINGS.get("auto_multiplier", False)
        return SETTINGS.get("auto_multiplier", False)

    @property
    def capital(self):
        if self.gui and hasattr(self.gui, "capital_entry"):
            try:
                return float(self.gui.capital_entry.get())
            except Exception:
                return SETTINGS.get("capital", 1000)
        return SETTINGS.get("capital", 1000)

    @property
    def interval(self):
        if self.gui and hasattr(self.gui, "interval"):
            try:
                return self.gui.interval.get()
            except Exception:
                return SETTINGS.get("interval", "15m")
        return SETTINGS.get("interval", "15m")
