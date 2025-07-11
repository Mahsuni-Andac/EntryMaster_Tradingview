# partial_close_manager.py

import threading
import time

class PartialCloseManager:
    """
    Auto Partial Close-Feature für deinen Bot:
    - Schließt regelmäßig (alle X Sekunden) einen konfigurierbaren Anteil der Position
    - Funktioniert mit Positionen als Dictionary wie in deinem System
    - Holt Werte und Statusanzeige direkt aus der GUI
    """
    def __init__(self, gui):
        self.gui = gui
        self.active = False
        self.thread = None
        self.position = None

    def start(self, position):
        """
        Starte Auto Partial Close für die aktuelle Position.
        Wird bei neuem Trade aus dem Bot aufgerufen.
        """
        self.stop()  # Stoppe ggf. alten Thread
        self.active = True
        self.position = position
        self.thread = threading.Thread(target=self._partial_close_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """
        Beende Auto Partial Close.
        Wird bei Positionsschluss oder Trade-Ende aus dem Bot aufgerufen.
        """
        self.active = False
        self.position = None

    def _partial_close_loop(self):
        """
        Interne Schleife, die regelmäßig Partial Closes ausführt, solange Position offen ist.
        """
        while self.active and self.position is not None:
            try:
                enabled = self.gui.apc_enabled.get()
                rate = float(self.gui.apc_rate.get())
                interval = float(self.gui.apc_interval.get())
                min_profit = float(self.gui.apc_min_profit.get())
            except Exception:
                self.gui.apc_status_label.config(text="❌ Auto Partial Close: Konfigurationsfehler!")
                break

            # Gewinn berechnen: (aktueller Kurs - Entry) * Menge * Richtung
            try:
                entry = self.position["entry"]
                current_price = self.gui.position["entry"]  # Fallback: Im Bot ggf. letzten Preis mitgeben!
                if "last_price" in self.position:
                    current_price = self.position["last_price"]
                else:
                    current_price = entry  # Notlösung

                direction = self.position["side"]
                amount = self.position.get("amount", 1)  # Anpassung an deinen Positionsdict!
                if direction == "long":
                    profit = (current_price - entry) * amount
                else:
                    profit = (entry - current_price) * amount
            except Exception as e:
                self.gui.apc_status_label.config(text=f"❌ Gewinnberechnung Fehler: {e}")
                break

            # Prüfe Mindestgewinn
            if enabled and profit > min_profit and amount > 0.0001:
                close_size = amount * rate / 100
                if close_size < 0.0001:
                    self.gui.apc_status_label.config(
                        text=f"⚠️ Zu kleine Restposition, Partial Close beendet."
                    )
                    break

                # Simuliere Teilverkauf – hier nur die Menge reduzieren!
                self.position["amount"] -= close_size
                if self.position["amount"] < 0:
                    self.position["amount"] = 0

                self.gui.apc_status_label.config(
                    text=f"✅ Partial Close: {rate:.1f}% ({close_size:.4f}) realisiert. Rest: {self.position['amount']:.4f}"
                )

                # Optional: Hier könntest du ein echtes Order-API aufrufen!

            else:
                self.gui.apc_status_label.config(
                    text=f"Partial Close: Wartet auf Mindestgewinn ({min_profit}$). Aktuell: {profit:.2f}$"
                )

            # Stoppen, wenn Position komplett aufgelöst
            if self.position["amount"] < 0.0001:
                self.gui.apc_status_label.config(
                    text=f"🏁 Position komplett geschlossen durch Partial Close!"
                )
                self.stop()
                break

            # Warten bis zum nächsten Intervall
            time.sleep(interval)

        # Nach Thread-Ende
        self.gui.apc_status_label.config(text="Auto Partial Close inaktiv.")

