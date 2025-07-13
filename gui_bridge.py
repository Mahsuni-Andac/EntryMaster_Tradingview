# gui_bridge.py

from config import SETTINGS

def smart_auto_multiplier(score, atr, balance, drawdown, max_risk_pct=1.0, base_multi=20, min_multi=1, max_multi=50):
    score_factor = 1.0 + max(0, (score - 0.7) * 2)
    atr_factor = max(0.5, min(1.2, 30 / (atr + 1)))
    dd_factor = 1.0 if drawdown < 0.1 else 0.5
    max_risk_usd = balance * (max_risk_pct / 100)

    smart_multi = base_multi * score_factor * atr_factor * dd_factor
    smart_multi = min(max(smart_multi, min_multi), max_multi)

    return round(smart_multi, 2)

class GUIBridge:
    def __init__(self, gui_instance=None):
        self.gui = gui_instance

    def _get_gui_value(self, name: str, fallback):
        if not self.gui or not hasattr(self.gui, name):
            return fallback
        try:
            return type(fallback)(getattr(self.gui, name).get())
        except Exception:
            return fallback

    def get_leverage(self, score=0.8, atr=25, balance=1000, drawdown=0.0):
        if self.auto_multiplier:
            return smart_auto_multiplier(
                score=score,
                atr=atr,
                balance=balance,
                drawdown=drawdown
            )
        else:
            return self.multiplier

    @property
    def multiplier(self):
        return self._get_gui_value("multiplier_entry", SETTINGS.get("multiplier", 20))

    @property
    def auto_multiplier(self):
        return self._get_gui_value("auto_multiplier", SETTINGS.get("auto_multiplier", False))

    @property
    def capital(self):
        return self._get_gui_value("capital_entry", SETTINGS.get("capital", 1000))

    @property
    def interval(self):
        return self._get_gui_value("interval", SETTINGS.get("interval", "15m"))

    @property
    def live_trading(self):
        return self._get_gui_value("live_trading", not SETTINGS.get("paper_mode", True))


    @property
    def manual_sl(self):
        return self._get_gui_value("manual_sl_var", None)

    @property
    def manual_tp(self):
        return self._get_gui_value("manual_tp_var", None)

    @property
    def manual_active(self):
        return self._get_gui_value("sl_tp_manual_active", False)

    @property
    def auto_active(self):
        return self._get_gui_value("sl_tp_auto_active", False)

    def set_manual_status(self, ok: bool):
        if self.gui and hasattr(self.gui, "set_manual_sl_status"):
            self.gui.set_manual_sl_status(ok)

    def set_auto_status(self, ok: bool):
        if self.gui and hasattr(self.gui, "set_auto_sl_status"):
            self.gui.set_auto_sl_status(ok)



    def update_live_pnl(self, pnl):
        if self.gui:
            self.gui.update_live_trade_pnl(pnl)

    def update_capital(self, capital, saved):
        if self.gui:
            self.gui.update_capital(capital, saved)

    def log_event(self, msg):
        if self.gui:
            self.gui.log_event(msg)

    def update_status(self, msg):
        if self.gui and hasattr(self.gui, "auto_status_label"):
            self.gui.auto_status_label.config(text=msg)

    def stop_bot(self):
        if self.gui:
            self.gui.running = False

    def update_filter_feedback(self, score):
        return
