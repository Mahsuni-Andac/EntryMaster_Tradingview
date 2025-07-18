# trading_gui_logic.py

import json
import os
import logging
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

TUNING_FILE = "tuning_config.json"

class TradingGUILogicMixin:
    def apply_recommendations(self):
        try:
            from datetime import datetime
            from global_state import ema_trend_global, atr_value_global
            from config import SETTINGS

            volatility = atr_value_global
            if volatility is None:
                self.log_event("⚠️ ATR noch nicht verfügbar - Empfehlungen übersprungen")
                return
            # REMOVED: SessionFilter
            hour = datetime.utcnow().hour
            if 6 <= hour < 14:
                session = "london"
            elif 13 <= hour < 21:
                session = "new_york"
            else:
                session = "asia"
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
                self.use_doji_blocker,
                self.use_time_filter,
            ]
            for var in all_vars:
                var.set(False)

            enable = []

            if spike:
                enable += [
                    self.andac_opt_safe_mode,
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
            multiplier = float(self.multiplier_var.get().replace(",", "."))
            auto_multi = self.auto_multiplier.get()
            capital = float(self.capital_var.get().replace(",", "."))
        except ValueError as e:
            messagebox.showerror("Eingabefehler", f"Ungültige Zahl: {e}")
            return
        except Exception as e:
            self.log_event(f"⚠️ Fehler bei Eingaben: {e}")
            return
        if capital <= 0:
            self.log_event("⚠️ Einsatz muss größer 0 sein")
            return
        interval = self.interval.get()
        if hasattr(self, "bridge") and self.bridge is not None:
            self.bridge.update_params(multiplier, auto_multi, capital, interval)
        if hasattr(self, "callback"):
            self.callback()

    def emergency_exit(self):
        try:
            if hasattr(self, "model"):
                self.model.running = False
            else:
                self.running = False
            if hasattr(self, "close_all_positions"):
                self.close_all_positions()
            self.log_event("❗️ Notausstieg ausgelöst! Alle Positionen werden geschlossen.")
        except Exception as e:
            print(f"❌ Fehler beim Notausstieg: {e}")

    def emergency_flat_position(self):
        if hasattr(self, "model"):
            self.model.force_exit = True
            self.model.running = False
        else:
            self.force_exit = True
            self.running = False
        self.log_event("⛔ Trade abbrechen: Die Position wird jetzt geschlossen.")

        if hasattr(self, 'position') and self.position is not None:
            from realtime_runner import cancel_trade
            self.position = cancel_trade(self.position, self)
            if self.position is None:
                logging.info("✅ Position wurde erfolgreich geschlossen und gel\u00f6scht.")
            else:
                logging.warning("\u26a0\ufe0f Position konnte nicht vollst\u00e4ndig entfernt werden.")
            self.log_event("✅ Position wurde erfolgreich geschlossen.")
        else:
            self.log_event("❌ Keine offene Position zum Abbrechen gefunden.")

    def abort_trade(self):
        if hasattr(self, "model"):
            self.model.force_exit = True
            self.model.running = False
        else:
            self.force_exit = True
            self.running = False

    def update_live_trade_pnl(self, pnl):
        color = "green" if pnl >= 0 else "red"
        self.pnl_value.config(text=f"📉 PnL: {pnl:.2f} $", foreground=color)

    def update_last_trade(self, side: str, entry: float, exit_price: float, pnl: float):
        text = f"{side.upper()} {entry:.2f}->{exit_price:.2f} ({pnl:.2f}$)"
        if hasattr(self, "last_trade_label"):
            self.last_trade_label.config(text=text)

    def update_stats(self, pnl: float):
        if hasattr(self, "model"):
            self.model.total_pnl += pnl
            if pnl >= 0:
                self.model.wins += 1
            else:
                self.model.losses += 1
            if hasattr(self, "total_pnl_label"):
                self.total_pnl_label.config(text=f"Gesamt PnL: {self.model.total_pnl:.2f} $")
            if hasattr(self, "trade_count_label"):
                self.trade_count_label.config(text=f"Trades {self.model.wins}/{self.model.losses}")

    def update_capital(self, capital):
        self.capital_value.config(text=f"💰 Kapital: ${capital:.2f}")

    def update_api_status(self, ok: bool, reason: str | None = None) -> None:
        if getattr(self, "_last_api_status", (None, None)) == (ok, reason):
            return
        self._last_api_status = (ok, reason)
        if hasattr(self, "model"):
            self.model.api_ok = ok
        else:
            self.api_ok = ok
        stamp = datetime.now().strftime("%H:%M:%S")
        if ok:
            text = "BitMEX API ✅"
            color = "green"
        else:
            text = f"BitMEX API ❌" + (f" – {reason} ({stamp})" if reason else f" ({stamp})")
            color = "red"
        if hasattr(self, "api_status_var"):
            self.api_status_var.set(text)
        if hasattr(self, "api_status_label"):
            self.api_status_label.config(foreground=color)
            if not self.api_status_label.winfo_ismapped():
                self.api_status_label.pack(side="left", padx=10)
        if hasattr(self, "neon_panel"):
            self.neon_panel.set_status("api", color, text)

    def update_feed_status(self, ok: bool, reason: str | None = None) -> None:
        if getattr(self, "_last_feed_status", (None, None)) == (ok, reason):
            return
        self._last_feed_status = (ok, reason)
        if hasattr(self, "model"):
            self.model.feed_ok = ok
        else:
            self.feed_ok = ok
        if reason == "REST-API-Call-14":
            color = "orange"
            text = reason
            if hasattr(self, "feed_mode_var"):
                self.feed_mode_var.set(reason)
        else:
            self._update_feed_mode_display(ok)
            color = "green" if ok else "red"
            text = "✅ Feed stabil" if ok else "❌ Kein Feed"
            if not ok and reason:
                if "Reconnect" in reason:
                    color = "orange"
                    text = f"🔄 {reason}"
                else:
                    text = f"❌ {reason}"

        if hasattr(self, "feed_status_var"):
            self.feed_status_var.set(text if not ok else "")
        if hasattr(self, "feed_status_label"):
            self.feed_status_label.config(foreground=color)
            if not ok and not self.feed_status_label.winfo_ismapped():
                self.feed_status_label.pack(side="left", padx=10)
            elif ok and self.feed_status_label.winfo_ismapped():
                self.feed_status_label.pack_forget()
        if hasattr(self, "neon_panel"):
            self.neon_panel.set_status("feed", color, text)
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "update_market_status"):
            self.api_frame.update_market_status(ok)

    def _update_feed_mode_display(self, ok: bool) -> None:
        if not ok:
            text = "Binance WebSocket ❌"
            color = "red"
        else:
            text = "Binance WebSocket OK"
            color = "green"

        if hasattr(self, "feed_mode_var"):
            self.feed_mode_var.set(text)
        if hasattr(self, "feed_mode_label"):
            self.feed_mode_label.config(foreground=color)
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "feed_mode_label"):
            self.api_frame.feed_mode_label.config(foreground=color)

    def update_exchange_status(self, exchange: str, ok: bool) -> None:
        if hasattr(self, "exchange_status_vars") and exchange in self.exchange_status_vars:
            cache = getattr(self, "exchange_status_cache", None)
            if cache is not None:
                cache[exchange] = ok
            if getattr(self, "_last_exchange_status", {}).get(exchange) == ok:
                return
            self._last_exchange_status = getattr(self, "_last_exchange_status", {})
            self._last_exchange_status[exchange] = ok
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
        self.update_stats(pnl)
        self.log_event(f"💰 Trade abgeschlossen: PnL {pnl:.2f} $")

    def log_event(self, msg):
        from central_logger import log_messages

        ignore = ["Antwort unvollständig"]
        if any(txt in msg for txt in ignore):
            return

        for line in log_messages(msg):
            self.log_box.insert("end", f"{line}\n")
        lines = self.log_box.get("1.0", "end-1c").splitlines()
        if len(lines) > 30:
            self.log_box.delete("1.0", f"{len(lines)-30 + 1}.0")
        self.log_box.see("end")

    def _log_error_once(self, text: str) -> None:
        if not hasattr(self, "_error_cache"):
            self._error_cache = set()
        if text in self._error_cache:
            return
        self._error_cache.add(text)
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_event(f"[{stamp}] ❌ Wirksamkeit: {text}")

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
            if hasattr(self, "neon_panel"):
                self.neon_panel.set_status("saved", "green", "Konfiguration gespeichert")
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

    def toggle_manual_sl_tp(self):
        ok = False
        if hasattr(self, "model"):
            sl = self.manual_sl_var.get()
            tp = self.manual_tp_var.get()
            ok = self.model.toggle_manual_sl_tp(sl, tp)
        if not ok:
            if hasattr(self, "manual_sl_button"):
                self.manual_sl_button.config(foreground="red")
            self.log_event("❌ Ungültige manuelle SL/TP Werte")
            return
        if hasattr(self, "manual_sl_button"):
            self.manual_sl_button.config(foreground="blue")
        if hasattr(self, "auto_sl_button"):
            self.auto_sl_button.config(foreground="black")
        self.log_event("📝 Manuelle SL/TP aktiviert")

    def activate_auto_sl_tp(self):
        if hasattr(self, "model"):
            self.model.activate_auto_sl_tp()
        else:
            self.sl_tp_auto_active.set(True)
            self.sl_tp_manual_active.set(False)
        if hasattr(self, "auto_sl_button"):
            self.auto_sl_button.config(foreground="blue")
        if hasattr(self, "manual_sl_button"):
            self.manual_sl_button.config(foreground="black")
        self.log_event("⚙️ Adaptive SL/TP aktiviert")

    def set_auto_sl_status(self, ok: bool) -> None:
        if hasattr(self, "model"):
            self.model.set_auto_sl_status(ok)
        else:
            self.sl_tp_auto_active.set(ok)
            if ok:
                self.sl_tp_manual_active.set(False)
        if hasattr(self, "auto_sl_button"):
            color = "green" if ok else "red"
            self.auto_sl_button.config(foreground=color)

    def set_manual_sl_status(self, ok: bool) -> None:
        if hasattr(self, "model"):
            self.model.set_manual_sl_status(ok)
        else:
            self.sl_tp_manual_active.set(ok)
            if ok:
                self.sl_tp_auto_active.set(False)
        if hasattr(self, "manual_sl_button"):
            color = "green" if ok else "red"
            self.manual_sl_button.config(foreground=color)

def stop_and_reset(self):
    if hasattr(self, "model"):
        self.model.force_exit = True
        self.model.running = False
    else:
        self.force_exit = True
        self.running = False
    try:
        self.log_event("🧹 Bot gestoppt – Keine Rücksetzung der Konfiguration vorgenommen.")
    except Exception as e:
        self.log_event(f"❌ Fehler beim Anhalten des Bots: {e}")

