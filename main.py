# main.py

import os
import json
import threading
import time
from datetime import datetime

import tkinter as tk
from colorama import Fore, Style, init
from central_logger import setup_logging

# Bot wrapper from andac_entry_master
from andac_entry_master import EntryMasterBot
from config_manager import config
from system_monitor import SystemMonitor
from trading_gui_core import TradingGUI
from trading_gui_logic import TradingGUILogicMixin
from api_key_manager import APICredentialManager
from gui_bridge import GUIBridge
from tkinter import messagebox
from requests.exceptions import RequestException
from global_state import entry_time_global, ema_trend_global, atr_value_global
import data_provider

root = tk.Tk()
data_provider.init_price_var(root)
price_var = data_provider.price_var

init(autoreset=True)
setup_logging()
bot = EntryMasterBot()

class EntryMasterGUI(TradingGUI, TradingGUILogicMixin):
    pass

def load_settings_from_file(filename="tuning_config.json"):
    """Load settings into the central config manager."""
    if not os.path.exists(filename):
        return
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        bot.apply_settings(data)
        config.load_json(filename)
    except Exception as e:
        print(f"⚠️ Konnte {filename} nicht laden: {e}")

def safe_run_bot(gui):
    """Start EntryMasterBot with GUI-friendly error handling."""
    try:
        bot.start(gui)
    except RequestException:
        messagebox.showerror(
            "Startfehler",
            "❌ API-Zugang ungültig oder Server nicht erreichbar.",
        )
        gui.running = False
    except (KeyError, ValueError) as exc:
        messagebox.showerror("Startfehler", f"❌ Konfigurationsfehler: {exc}")
        gui.running = False
    except Exception as exc:
        messagebox.showerror("Startfehler", f"❌ Botstart fehlgeschlagen: {exc}")
        gui.running = False

def bot_control(gui):
    while True:
        cmd = input("💻 CMD> ").strip().lower()
        if cmd == "start":
            if not gui.running:
                load_settings_from_file()
                bot.apply_settings({"paper_mode": not gui.live_trading.get()})
                mode_text = "LIVE-MODUS" if gui.live_trading.get() else "SIMULATIONS-MODUS"
                print(f"🚀 Bot gestartet: {mode_text}")
                gui.running = True
                threading.Thread(target=safe_run_bot, args=(gui,), daemon=True).start()
            else:
                print("⚠️ Bot läuft bereits")
        elif cmd == "stop":
            gui.force_exit = True
            print("⛔ Trade-Abbruch gesendet")
        elif cmd == "status":
            try:
                pnl = round(getattr(gui, "live_pnl", 0.0), 1)
                farbe = (
                    Fore.GREEN + "🟢" if pnl > 0 else
                    Fore.RED + "🔴" if pnl < 0 else
                    Fore.YELLOW + "➖"
                )
                laufzeit = int(time.time() - entry_time_global) if entry_time_global else 0
                uhrzeit = datetime.now().strftime("%H:%M:%S")
                datum = datetime.now().strftime("%d.%m.%Y")
                capital = 0.0
                if hasattr(gui, "capital_var"):
                    try:
                        capital = float(gui.capital_var.get())
                    except Exception:
                        pass
                leverage = bot.settings.get("leverage", 20)
                if hasattr(gui, "multiplier_var") and hasattr(gui.multiplier_var, "get"):
                    try:
                        leverage = float(gui.multiplier_var.get())
                    except Exception:
                        pass
                trade_info = "--- (wartet)"
                if hasattr(gui, "position") and gui.position:
                    trade_info = f"{gui.position['side'].upper()} @ {gui.position['entry']}"
                filter_status = {
                    "RSI/EMA": gui.andac_opt_rsi_ema.get(),
                    "SAFE": gui.andac_opt_safe_mode.get(),
                    "ENG": gui.andac_opt_engulf.get(),
                    "BRUCH": gui.andac_opt_engulf_bruch.get(),
                    "BIG": gui.andac_opt_engulf_big.get(),
                    "DELAY": gui.andac_opt_confirm_delay.get(),
                    "MTF": gui.andac_opt_mtf_confirm.get(),
                    "VOL": gui.andac_opt_volumen_strong.get(),
                }
                filter_line = "🎛 Andac: " + " ".join(
                    f"{k}{'✅' if v else '❌'}" for k, v in filter_status.items()
                )
                status = (
                    f"{farbe} Aktueller PnL: ${pnl:.1f} | Laufzeit: {laufzeit}s | ⏰ {uhrzeit} | 📅 {datum}\n"
                    f"💼 Kapital: ${capital:.2f} | 📊 Lev: x{leverage} | 📍 Trade: {trade_info}\n"
                    f"📉 ATR: ${atr_value_global if atr_value_global is not None else 0.0:.1f} | 📈 EMA: {ema_trend_global} | 🚀 Modus: {'LIVE' if gui.live_trading.get() else 'SIMULATION'}\n"
                    f"{filter_line}"
                )
                print(status + Style.RESET_ALL)
            except Exception as e:
                print(f"❌ Fehler bei 'status': {e}")
        elif cmd == "restart":
            from global_state import reset_global_state
            gui.force_exit = True
            reset_global_state()
            print("♻️ Bot zurückgesetzt")
        else:
            print("❓ Unbekannter Befehl. Verfügbar: start / stop / status / restart")

def on_gui_start(gui):
    if gui.running:
        print("⚠️ Bot läuft bereits (GUI-Schutz)")
        return
    load_settings_from_file()
    bot.apply_settings({
        "interval": gui.interval.get(),
        "paper_mode": not gui.live_trading.get(),
    })
    mode_text = "LIVE-MODUS" if gui.live_trading.get() else "SIMULATIONS-MODUS"
    print(f"🚀 Bot gestartet: {mode_text}")
    gui.running = True
    threading.Thread(target=safe_run_bot, args=(gui,), daemon=True).start()

def main():
    load_settings_from_file()
    config.load_env()

    # Candle WebSocket will start automatically when needed
    cred_manager = APICredentialManager()
    gui = EntryMasterGUI(root, cred_manager=cred_manager)
    gui_bridge = GUIBridge(gui_instance=gui, bot=bot)
    gui.callback = lambda: on_gui_start(gui)

    gui.system_monitor = SystemMonitor(gui)
    gui.system_monitor.start()

    threading.Thread(target=bot_control, args=(gui,), daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()

