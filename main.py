# main.py

import os
import json
import threading
import time
from datetime import datetime

import tkinter as tk
from colorama import Fore, Style, init

from config import SETTINGS
from exchange_manager import detect_available_exchanges
from credential_checker import check_all_credentials
from gui import (
    TradingGUI,
    TradingGUILogicMixin,
    setup_score_bar_styles,
)
from api_key_manager import APICredentialManager
from gui_bridge import GUIBridge
from realtime_runner import run_bot_live
from global_state import entry_time_global, ema_trend_global, atr_value_global

init(autoreset=True)

class EntryMasterGUI(TradingGUI, TradingGUILogicMixin):
    """Kombiniert GUI und Logik für EntryMaster_Tradingview."""
    pass

def load_settings_from_file(filename="tuning_config.json"):
    """Lädt Settings aus einer JSON-Datei und überschreibt Defaults."""
    if not os.path.exists(filename):
        return
    try:
        with open(filename, "r", encoding="utf-8") as f:
            SETTINGS.update(json.load(f))
    except Exception as e:
        print(f"⚠️ Konnte {filename} nicht laden: {e}")

def bot_control(gui):
    """Kommandozeilensteuerung des Bots."""
    while True:
        cmd = input("💻 CMD> ").strip().lower()
        if cmd == "start":
            if not gui.running:
                load_settings_from_file()
                check_all_credentials(SETTINGS)
                print("🚀 Bot gestartet: TEST-MODUS" if SETTINGS.get("test_mode") else "🚀 Bot gestartet: LIVE-MODUS")
                gui.running = True
                threading.Thread(target=run_bot_live, args=(SETTINGS, gui), daemon=True).start()
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
                # Kapital direkt aus capital_var (StringVar)
                capital = 0.0
                if hasattr(gui, "capital_var"):
                    try:
                        capital = float(gui.capital_var.get())
                    except Exception:
                        pass
                # Hebel (Leverage)
                leverage = SETTINGS.get("leverage", 20)
                if hasattr(gui, "multiplier_var") and hasattr(gui.multiplier_var, "get"):
                    try:
                        leverage = float(gui.multiplier_var.get())
                    except Exception:
                        pass
                # Trade-Info
                trade_info = "--- (wartet)"
                if hasattr(gui, "position") and gui.position:
                    trade_info = f"{gui.position['side'].upper()} @ {gui.position['entry']}"
                # Filterstatus
                filter_status = {
                    "RSI/EMA": gui.andac_opt_rsi_ema.get(),
                    "SAFE": gui.andac_opt_safe_mode.get(),
                    "ENG": gui.andac_opt_engulf.get(),
                    "BRUCH": gui.andac_opt_engulf_bruch.get(),
                    "BIG": gui.andac_opt_engulf_big.get(),
                    "DELAY": gui.andac_opt_confirm_delay.get(),
                    "MTF": gui.andac_opt_mtf_confirm.get(),
                    "VOL": gui.andac_opt_volumen_strong.get(),
                    "SES": gui.andac_opt_session_filter.get(),
                }
                filter_line = "🎛 Andac: " + " ".join(
                    f"{k}{'✅' if v else '❌'}" for k, v in filter_status.items()
                )
                status = (
                    f"{farbe} Aktueller PnL: ${pnl:.1f} | Laufzeit: {laufzeit}s | ⏰ {uhrzeit} | 📅 {datum}\n"
                    f"💼 Kapital: ${capital:.2f} | 📊 Lev: x{leverage} | 📍 Trade: {trade_info}\n"
                    f"📉 ATR: ${atr_value_global:.1f} | 📈 EMA: {ema_trend_global} | "
                    f"{'🧪 Modus: TEST' if SETTINGS.get('test_mode') else '🚀 Modus: LIVE'}\n"
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
    check_all_credentials(SETTINGS)
    SETTINGS["interval"] = gui.interval.get()
    print("🚀 Bot gestartet: TEST-MODUS" if SETTINGS.get("test_mode") else "🚀 Bot gestartet: LIVE-MODUS")
    gui.running = True
    threading.Thread(target=run_bot_live, args=(SETTINGS, gui), daemon=True).start()

def main():
    load_settings_from_file()
    detect_available_exchanges(SETTINGS)
    check_all_credentials(SETTINGS)
    root = tk.Tk()
    setup_score_bar_styles(root)
    cred_manager = APICredentialManager()
    gui = EntryMasterGUI(root, cred_manager=cred_manager)
    gui_bridge = GUIBridge(gui_instance=gui)
    gui.callback = lambda: on_gui_start(gui)
    threading.Thread(target=bot_control, args=(gui,), daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()

