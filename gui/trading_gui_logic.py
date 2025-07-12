# trading_gui_logic.py
# Changelog: added capital > 0 validation in start_bot

import json
import os
import tkinter as tk
from datetime import datetime

TUNING_FILE = "tuning_config.json"

class TradingGUILogicMixin:
    def apply_recommendations(self):
        """Aktiviert sinnvolle Filter-Kombinationen anhand der Marktlage."""
        try:
            from session_filter import SessionFilter
            from global_state import ema_trend_global, atr_value_global
            from config import SETTINGS

            # --- Umfeld ermitteln ---
            volatility = atr_value_global
            session = SessionFilter().get_current_session()
            performance = getattr(self, "live_pnl", 0.0)
            trend = ema_trend_global

            high_vol = volatility > 30
            spike = volatility > 80

            all_vars = [
                self.andac_opt_rsi_ema,
                self.andac_opt_safe_mode,
                self.andac_opt_engulf,
                self.andac_opt_engulf_bruch,
                self.andac_opt_engulf_big,
                self.andac_opt_confirm_delay,
                self.andac_opt_mtf_confirm,
                self.andac_opt_volumen_strong,
                self.andac_opt_session_filter,
                self.use_doji_blocker,
                self.use_time_filter,
            ]
            for var in all_vars:
                var.set(False)

            enable = []

            if spike:
                enable += [
                    self.andac_opt_safe_mode,
                    self.andac_opt_session_filter,
                    self.use_doji_blocker,
                    self.andac_opt_volumen_strong,
                ]
            elif high_vol:
                enable += [
                    self.andac_opt_engulf,
                    self.andac_opt_engulf_bruch,
                    self.andac_opt_volumen_strong,
                ]
            else:
                enable += [self.andac_opt_rsi_ema, self.andac_opt_safe_mode]

            if session in ("london", "new_york"):
                enable += [self.andac_opt_confirm_delay, self.andac_opt_mtf_confirm]
            else:
                enable.append(self.andac_opt_safe_mode)

            if performance < 0:
                enable += [self.andac_opt_safe_mode, self.use_doji_blocker]
            elif performance > 0:
                enable.append(self.andac_opt_engulf)

            if trend == "⬆️":
                enable.append(self.andac_opt_engulf_big)
            elif trend == "⬇️":
                enable.append(self.andac_opt_engulf_bruch)

            for var in set(enable):
                var.set(True)

            SETTINGS.update({
                "opt_rsi_ema": self.andac_opt_rsi_ema.get(),
                "opt_safe_mode": self.andac_opt_safe_mode.get(),
                "opt_engulf": self.andac_opt_engulf.get(),
                "opt_engulf_bruch": self.andac_opt_engulf_bruch.get(),
                "opt_engulf_big": self.andac_opt_engulf_big.get(),
                "opt_confirm_delay": self.andac_opt_confirm_delay.get(),
                "opt_mtf_confirm": self.andac_opt_mtf_confirm.get(),
                "opt_volumen_strong": self.andac_opt_volumen_strong.get(),
                "opt_session_filter": self.andac_opt_session_filter.get(),
            })

            self.log_event("✅ Auto-Empfehlungen angewendet")
        except Exception as e:
            self.log_event(f"⚠️ Fehler beim Anwenden: {e}")

    def disable_all_filters(self):
        try:
            for var in [
                self.andac_opt_rsi_ema,
                self.andac_opt_safe_mode,
                self.andac_opt_engulf,
                self.andac_opt_engulf_bruch,
                self.andac_opt_engulf_big,
                self.andac_opt_confirm_delay,
                self.andac_opt_mtf_confirm,
                self.andac_opt_volumen_strong,
                self.andac_opt_session_filter,
                self.use_time_filter,
                self.use_doji_blocker,
            ]:
                var.set(False)
            self.log_event("🧹 Alle Filter & Optionen deaktiviert")
        except Exception as e:
            self.log_event(f"⚠️ Fehler beim Deaktivieren: {e}")

    def update_auto_status(self):
        if self.auto_apply_recommendations.get():
            self.auto_status_label.config(text="🟢 Auto-Empfehlung aktiv")
        else:
            self.auto_status_label.config(text="")

    def start_bot(self):
        try:
            multiplier = float(self.multiplier_var.get())
            auto_multi = self.auto_multiplier.get()
            capital = float(self.capital_var.get())
            if capital <= 0:
                self.log_event("⚠️ Einsatz muss größer 0 sein")
                return
            interval = self.interval.get()
            if hasattr(self, "bridge") and self.bridge is not None:
                self.bridge.update_params(multiplier, auto_multi, capital, interval)
        except Exception as e:
            self.log_event(f"⚠️ Fehler bei Eingaben: {e}")
        if hasattr(self, "callback"):
            self.callback()

    def emergency_exit(self):
        try:
            self.running = False  # Bot-Schleife stoppen
            if hasattr(self, "close_all_positions"):
                self.close_all_positions()
            self.log_event("❗️ Notausstieg ausgelöst! Alle Positionen werden geschlossen.")
        except Exception as e:
            print(f"❌ Fehler beim Notausstieg: {e}")

    def emergency_flat_position(self):
        self.force_exit = True
        self.running = False
        self.log_event("⛔ Trade abbrechen: Die Position wird jetzt geschlossen.")
        
        # Überprüfen, ob eine Position vorhanden ist, bevor sie geschlossen wird
        if hasattr(self, 'position') and self.position is not None:
            # Falls eine Position offen ist, rufen wir die Methode auf, um sie zu schließen
            self.position = cancel_trade(self.position, self)  # Schließt die Position und setzt sie auf None
            self.log_event("✅ Position wurde erfolgreich geschlossen.")
        else:
            self.log_event("❌ Keine offene Position zum Abbrechen gefunden.")

    def abort_trade(self):
        self.force_exit = True
        self.running = False

    def update_live_trade_pnl(self, pnl):
        color = "green" if pnl >= 0 else "red"
        self.pnl_value.config(text=f"📉 PnL: {pnl:.2f} $", foreground=color)

    def update_capital(self, capital):
        self.capital_value.config(text=f"💰 Kapital: ${capital:.2f}")

    def update_api_status(self, ok: bool, reason: str | None = None) -> None:
        """Display API problems only."""
        self.api_ok = ok
        if ok:
            if hasattr(self, "api_status_label") and self.api_status_label.winfo_ismapped():
                self.api_status_label.pack_forget()
            if hasattr(self, "api_status_var"):
                self.api_status_var.set("")
        else:
            stamp = datetime.now().strftime("%H:%M:%S")
            text = f"API ❌" + (f" – {reason} ({stamp})" if reason else f" ({stamp})")
            if hasattr(self, "api_status_var"):
                self.api_status_var.set(text)
            if hasattr(self, "api_status_label"):
                self.api_status_label.config(foreground="red")
                if not self.api_status_label.winfo_ismapped():
                    self.api_status_label.pack(side="left", padx=10)

    def update_feed_status(self, ok: bool, reason: str | None = None) -> None:
        """Display feed problems only."""
        self.feed_ok = ok
        if ok:
            if hasattr(self, "feed_status_label") and self.feed_status_label.winfo_ismapped():
                self.feed_status_label.pack_forget()
            if hasattr(self, "feed_status_var"):
                self.feed_status_var.set("")
        else:
            stamp = datetime.now().strftime("%H:%M:%S")
            text = f"Feed ❌" + (f" – {reason} ({stamp})" if reason else f" ({stamp})")
            if hasattr(self, "feed_status_var"):
                self.feed_status_var.set(text)
            if hasattr(self, "feed_status_label"):
                self.feed_status_label.config(foreground="red")
                if not self.feed_status_label.winfo_ismapped():
                    self.feed_status_label.pack(side="left", padx=10)

    def update_exchange_status(self, exchange: str, ok: bool) -> None:
        if hasattr(self, "exchange_status_vars") and exchange in self.exchange_status_vars:
            lbl = self.exchange_status_labels.get(exchange)
            if ok:
                if lbl and lbl.winfo_ismapped():
                    lbl.pack_forget()
                self.exchange_status_vars[exchange].set("")
            else:
                stamp = datetime.now().strftime("%H:%M:%S")
                text = f"{exchange} ❌ ({stamp})"
                self.exchange_status_vars[exchange].set(text)
                if lbl:
                    lbl.config(foreground="red")
                    if not lbl.winfo_ismapped():
                        lbl.pack(side="left", padx=5)

    def update_pnl(self, pnl):
        self.log_event(f"💰 Trade abgeschlossen: PnL {pnl:.2f} $")

    def log_event(self, msg):
        self.log_box.insert("end", f"{msg}\n")
        self.log_box.see("end")

    def save_to_file(self, filename=TUNING_FILE):
        state = {}
        for k, v in vars(self).items():
            if isinstance(v, tk.Variable):
                state[k] = v.get()
            elif isinstance(v, (str, float, int, bool)):
                state[k] = v
        if hasattr(self, "time_filters"):
            state["time_filters"] = [
                (start.get(), end.get()) for (start, end) in self.time_filters
            ]
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            self.log_event("💾 Einstellungen gespeichert")
        except Exception as e:
            self.log_event(f"Fehler beim Speichern: {e}")

    def load_from_file(self, filename=TUNING_FILE):
        if not os.path.exists(filename):
            self.log_event(f"Keine Konfigurationsdatei {filename} gefunden")
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                state = json.load(f)
            for k, v in state.items():
                if hasattr(self, k):
                    var = getattr(self, k)
                    if isinstance(var, tk.Variable):
                        var.set(v)
            if "time_filters" in state and hasattr(self, "time_filters"):
                loaded_filters = state["time_filters"]
                if len(loaded_filters) == len(self.time_filters):
                    for (start_val, end_val), (start, end) in zip(loaded_filters, self.time_filters):
                        start.set(start_val)
                        end.set(end_val)
            self.log_event("⏏️ Einstellungen geladen")
        except Exception as e:
            self.log_event(f"Fehler beim Laden: {e}")

    def _collect_settings(self):
        return {
            k: (
                self._convert_strvar(v) if isinstance(v, tk.StringVar)
                else v.get()
            )
            for k, v in self.__dict__.items()
            if isinstance(v, (tk.StringVar, tk.BooleanVar))
        }

    def _convert_strvar(self, var):
        try:
            val = var.get()
            if val.replace(".", "", 1).isdigit():
                return float(val) if "." in val else int(val)
            return val
        except:
            return var.get()

def stop_and_reset(self):
    self.force_exit = True
    self.running = False
    try:
        # Einfach nur den Bot anhalten, ohne die Konfiguration zurückzusetzen
        self.log_event("🧹 Bot gestoppt – Keine Rücksetzung der Konfiguration vorgenommen.")
    except Exception as e:
        self.log_event(f"❌ Fehler beim Anhalten des Bots: {e}")

