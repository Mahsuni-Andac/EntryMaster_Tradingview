# gui_bridge.py

from config import SETTINGS

def smart_auto_multiplier(score, atr, balance, drawdown, max_risk_pct=1.0, base_multi=20, min_multi=1, max_multi=50):
    """
    Profi-Auto-Multiplikator: Max. Wachstum, Risiko-Kontrolle.
    """
    # Score-Boost: ab 0.7+ geht's hoch
    score_factor = 1.0 + max(0, (score - 0.7) * 2)
    # ATR-Schutz: zu hohe Volatilität = weniger Hebel
    atr_factor = max(0.5, min(1.2, 30 / (atr + 1)))
    # Drawdown-Bremse: ab -10% Hebel halbieren
    dd_factor = 1.0 if drawdown < 0.1 else 0.5
    # Max. Risko absolut pro Trade (optional für Cap)
    max_risk_usd = balance * (max_risk_pct / 100)

    smart_multi = base_multi * score_factor * atr_factor * dd_factor
    smart_multi = min(max(smart_multi, min_multi), max_multi)

    # (Optional) Multi auf max_risk_usd deckeln (erweiterbar, siehe oben)
    return round(smart_multi, 2)

class GUIBridge:
    def __init__(self, gui_instance=None):
        self.gui = gui_instance

    def get_leverage(self, score=0.8, atr=25, balance=1000, drawdown=0.0):
        """
        Entscheidet ob Auto/Manuell und gibt den korrekten Multiplikator/Leverage zurück.
        Die Argumente sollten beim Trade übergeben werden!
        """
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

    def update_score_display(self, score, symbol, allowed=True, reason=None):
        if self.gui and hasattr(self.gui, "score_display"):
            self.gui.score_display.update_score(score, symbol, allowed, reason)
        self.update_filter_feedback(score)

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
        if not self.gui:
            return
        try:
            score = float(score)
            if score >= 0.9:
                self.gui.use_breakout_filter.set(True)
                self.gui.use_volume_boost.set(True)
                self.gui.breakout_rec_label.config(text="🚀 Boost aktivieren")
                self.gui.volboost_rec_label.config(text="🚀 Volume Surge aktiv")
            elif score >= 0.8:
                self.gui.breakout_rec_label.config(text="🟢 Breakout sinnvoll")
                self.gui.volboost_rec_label.config(text="🟢 Volumen ok")
            elif score >= 0.7:
                self.gui.breakout_rec_label.config(text="🟢 Bestätigung leicht")
            elif score >= 0.6:
                self.gui.breakout_rec_label.config(text="🟡 RSI/EMA prüfen")
            else:
                self.gui.breakout_rec_label.config(text="🔻 Entry vermeiden")
        except Exception as e:
            self.log_event(f"⚠️ Fehler bei Score-Auswertung: {e}")
