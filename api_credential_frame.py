# api_credential_frame.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict

from api_key_manager import APICredentialManager
from status_events import StatusDispatcher
from config import SETTINGS
from bitmex_interface import set_credentials, check_credentials

EXCHANGES = ["BitMEX"]

class APICredentialFrame(ttk.LabelFrame):

    def __init__(self, master: tk.Misc, cred_manager: APICredentialManager, log_callback=None) -> None:
        super().__init__(master, text="Exchange API")
        self.cred_manager = cred_manager
        self.log_callback = log_callback

        self.active_exchange = tk.StringVar(value=EXCHANGES[0])

        self.vars: Dict[str, Dict[str, tk.Variable]] = {}
        self.status_vars: Dict[str, tk.StringVar] = {}
        self.status_labels: Dict[str, ttk.Label] = {}

        self.data_source_mode = tk.StringVar(value="websocket")

        ttk.Label(self, text="Exchange:").grid(row=0, column=0, sticky="w")
        ttk.Label(self, text=EXCHANGES[0]).grid(row=0, column=1, sticky="w")

        start_row = 1
        for idx, exch in enumerate(EXCHANGES):
            row = start_row + idx
            status = tk.StringVar(value="⚪")
            self.status_vars[exch] = status
            key = tk.StringVar()
            secret = tk.StringVar()
            wallet = tk.StringVar()
            priv = tk.StringVar()
            self.vars[exch] = {
                "key": key,
                "secret": secret,
                "wallet": wallet,
                "priv": priv,
            }
            ttk.Label(self, text=f"API {exch}").grid(row=row, column=0, sticky="w")
            entry1 = ttk.Entry(self, textvariable=key, width=20, show="*")
            entry2 = ttk.Entry(self, textvariable=secret, width=20, show="*")
            entry1.grid(row=row, column=1, padx=2)
            entry2.grid(row=row, column=2, padx=2)
            lbl = ttk.Label(self, textvariable=status, foreground="grey")
            lbl.grid(row=row, column=3, padx=4)
            self.status_labels[exch] = lbl
            self.vars[exch]["entry1"] = entry1
            self.vars[exch]["entry2"] = entry2

        control_row = ttk.Frame(self)
        control_row.grid(row=start_row + len(EXCHANGES), column=0, columnspan=4, sticky="w", pady=5)
        ttk.Button(control_row, text="Speichern", command=self._save).pack(side="left")


        self.market_status = tk.StringVar(value="")

        status_row = ttk.Frame(self)
        status_row.grid(row=start_row + len(EXCHANGES) + 1, column=0, columnspan=4, sticky="w")

        self.market_status_label = ttk.Label(status_row, textvariable=self.market_status, foreground="red")
        self.market_status_label.pack(side="left")

        self.system_status = tk.StringVar(value="")
        self.system_status_label = ttk.Label(status_row, textvariable=self.system_status, foreground="green")
        self.system_status_label.pack(side="left", padx=(10, 0))

        self.feed_mode = tk.StringVar(value="")
        self.feed_mode_label = ttk.Label(status_row, textvariable=self.feed_mode, foreground="green")
        self.feed_mode_label.pack(side="left", padx=(10, 0))

        term_frame = tk.Frame(self, bg="black")
        term_frame.grid(row=0, column=4, rowspan=len(EXCHANGES)+1, padx=5, sticky="ne")
        self.price_terminal = tk.Text(term_frame, height=6, width=24, bg="black", fg="green", state="disabled")
        self.price_terminal.pack()

        self.check_market_feed()



    def log_price(self, text: str, error: bool = False) -> None:
        color = "red" if error else "green"
        self.price_terminal.config(state="normal", fg=color)
        self.price_terminal.insert("end", text + "\n")
        lines = self.price_terminal.get("1.0", "end-1c").splitlines()
        if len(lines) > 30:
            self.price_terminal.delete("1.0", f"{len(lines)-30 + 1}.0")
        self.price_terminal.see("end")
        self.price_terminal.config(state="disabled")

    def update_market_status(self, ok: bool) -> None:
        text = "✅ Marktdaten kommen an" if ok else "❌ Keine Marktdaten – bitte prüfen"
        color = "green" if ok else "red"
        self.market_status.set(text)
        self.market_status_label.config(foreground=color)

    def check_market_feed(self) -> None:
        from data_provider import WebSocketStatus

        ok = WebSocketStatus.is_running()
        self.update_market_status(ok)

    def _save(self) -> None:
        exch = EXCHANGES[0]
        data = self.vars[exch]
        key = data["key"].get().strip()
        secret = data["secret"].get().strip()
        if not key or not secret:
            ok, msg = False, "API Key und Secret erforderlich"
        else:
            self.cred_manager.set_credentials(key, secret)
            set_credentials(key, secret)
            ok = check_credentials()
            msg = "API Daten gespeichert" if ok else "API Test fehlgeschlagen"
        if ok:
            SETTINGS[f"{exch.lower()}_key"] = key
            SETTINGS[f"{exch.lower()}_secret"] = secret
        else:
            self.cred_manager.clear()
            SETTINGS.pop(f"{exch.lower()}_key", None)
            SETTINGS.pop(f"{exch.lower()}_secret", None)
        SETTINGS["data_source_mode"] = "websocket"

        self.status_vars[exch].set("✅" if ok else "❌")
        self.status_labels[exch].config(foreground="green" if ok else "red")
        if self.log_callback:
            self.log_callback(msg)
        else:
            messagebox.showinfo("Status", msg)

        StatusDispatcher.dispatch("api", ok, None if ok else "Keine API aktiv")
        self.check_market_feed()


    def _test_api(self):
        print("🔍 Teste API-Zugriff (Platzhalter)")
