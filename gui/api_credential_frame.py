import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict

from api_key_manager import APICredentialManager
from credential_checker import check_exchange_credentials
from status_events import StatusDispatcher
from config import SETTINGS

EXCHANGES = ["MEXC", "dYdX", "Binance", "Bybit", "BitMEX"]

class APICredentialFrame(ttk.LabelFrame):
    """GUI frame for managing multiple exchange credentials."""

    def __init__(self, master: tk.Misc, cred_manager: APICredentialManager, log_callback=None, select_callback=None) -> None:
        super().__init__(master, text="Exchange API")
        self.cred_manager = cred_manager
        self.log_callback = log_callback
        self.select_callback = select_callback

        self.active_exchange = tk.StringVar(value=EXCHANGES[0])

        self.vars: Dict[str, Dict[str, tk.Variable]] = {}
        self.status_vars: Dict[str, tk.StringVar] = {}
        self.status_labels: Dict[str, ttk.Label] = {}

        ttk.Label(self, text="Trading-Exchange:").grid(row=0, column=0, sticky="w")
        box = ttk.Combobox(self, state="readonly", values=EXCHANGES, textvariable=self.active_exchange, width=10)
        box.grid(row=0, column=1, sticky="w")
        box.bind("<<ComboboxSelected>>", lambda _e: self._select_exchange(self.active_exchange.get()))

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
            if exch == "dYdX":
                entry1 = ttk.Entry(self, textvariable=wallet, width=20)
                entry2 = ttk.Entry(self, textvariable=priv, width=34, show="*")
            else:
                entry1 = ttk.Entry(self, textvariable=key, width=20, show="*")
                entry2 = ttk.Entry(self, textvariable=secret, width=20, show="*")
            entry1.grid(row=row, column=1, padx=2)
            entry2.grid(row=row, column=2, padx=2)
            lbl = ttk.Label(self, textvariable=status, foreground="grey")
            lbl.grid(row=row, column=3, padx=4)
            self.status_labels[exch] = lbl
            self.vars[exch]["entry1"] = entry1
            self.vars[exch]["entry2"] = entry2

        ttk.Button(self, text="Speichern", command=self._save).grid(row=start_row + len(EXCHANGES), column=0, pady=5, sticky="w")

        self._select_exchange(self.active_exchange.get())
        if self.select_callback:
            self.select_callback(self.active_exchange.get())

        # Mini price monitor
        term_frame = tk.Frame(self, bg="black")
        term_frame.grid(row=0, column=4, rowspan=len(EXCHANGES)+1, padx=5, sticky="ne")
        self.price_terminal = tk.Text(term_frame, height=6, width=24, bg="black", fg="green", state="disabled")
        self.price_terminal.pack()

    # ------------------------------------------------------------------
    def _select_exchange(self, exch: str) -> None:
        for name in EXCHANGES:
            data = self.vars[name]
            state = "normal" if name == exch else "disabled"
            data["entry1"].config(state=state)
            data["entry2"].config(state=state)
            if name != exch:
                self.status_vars[name].set("⚪")
                self.status_labels[name].config(foreground="grey")
        if self.select_callback:
            self.select_callback(exch)

    def log_price(self, text: str, error: bool = False) -> None:
        color = "red" if error else "green"
        self.price_terminal.config(state="normal", fg=color)
        self.price_terminal.insert("end", text + "\n")
        lines = self.price_terminal.get("1.0", "end-1c").splitlines()
        if len(lines) > 30:
            self.price_terminal.delete("1.0", f"{len(lines)-30 + 1}.0")
        self.price_terminal.see("end")
        self.price_terminal.config(state="disabled")

    # ------------------------------------------------------------------
    def _save(self) -> None:
        exch = self.active_exchange.get()
        data = self.vars[exch]
        if exch == "dYdX":
            wallet = data["wallet"].get().strip()
            priv = data["priv"].get().strip()
            ok, msg = check_exchange_credentials(exch, wallet=wallet, private_key=priv)
            if ok:
                SETTINGS["dydx_wallet"] = wallet
                SETTINGS["dydx_private_key"] = priv
            else:
                SETTINGS.pop("dydx_wallet", None)
                SETTINGS.pop("dydx_private_key", None)
        else:
            key = data["key"].get().strip()
            secret = data["secret"].get().strip()
            if not key or not secret:
                ok, msg = False, "API Key und Secret erforderlich"
            else:
                ok, msg = check_exchange_credentials(exch, key=key, secret=secret)
            if ok:
                SETTINGS[f"{exch.lower()}_key"] = key
                SETTINGS[f"{exch.lower()}_secret"] = secret
            else:
                SETTINGS.pop(f"{exch.lower()}_key", None)
                SETTINGS.pop(f"{exch.lower()}_secret", None)

        self.status_vars[exch].set("✅" if ok else "❌")
        self.status_labels[exch].config(foreground="green" if ok else "red")
        if self.log_callback:
            self.log_callback(msg)
        else:
            messagebox.showinfo("Status", msg)

        SETTINGS["trading_backend"] = exch.lower()
        SETTINGS["enabled_exchanges"] = [e.lower() for e in EXCHANGES]
        StatusDispatcher.dispatch("api", ok, None if ok else "Keine API aktiv")

