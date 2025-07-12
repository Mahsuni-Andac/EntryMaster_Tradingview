import tkinter as tk
from tkinter import ttk, messagebox
from api_key_manager import APICredentialManager
from credential_checker import check_exchange_credentials
from config import SETTINGS

EXCHANGES = ["MEXC", "dYdX", "Binance", "Bybit", "BitMEX"]

class APICredentialFrame(ttk.LabelFrame):
    """GUI-Frame zur Eingabe von API-Zugangsdaten."""

    def __init__(self, master: tk.Misc, cred_manager: APICredentialManager, log_callback=None, monitor=None) -> None:
        super().__init__(master, text="Exchange API")
        self.cred_manager = cred_manager
        self.log_callback = log_callback
        # optionaler SystemMonitor für Sofort-Checks
        self.monitor = monitor

        ttk.Label(self, text="Börse:").grid(row=0, column=0, sticky="w")
        self.exchange_var = tk.StringVar(value=EXCHANGES[0])
        box = ttk.Combobox(self, textvariable=self.exchange_var, values=EXCHANGES, state="readonly")
        box.grid(row=0, column=1, sticky="w")
        box.bind("<<ComboboxSelected>>", self._on_exchange_change)

        self.key_var = tk.StringVar()
        self.secret_var = tk.StringVar()
        self.wallet_var = tk.StringVar()
        self.priv_var = tk.StringVar()

        # Statusanzeige für Credential-Checks
        self.status_var = tk.StringVar(value="inaktiv")

        self.key_entry = ttk.Entry(self, textvariable=self.key_var, show="*", width=40)
        self.secret_entry = ttk.Entry(self, textvariable=self.secret_var, show="*", width=40)
        self.wallet_entry = ttk.Entry(self, textvariable=self.wallet_var, width=42)
        self.private_entry = ttk.Entry(self, textvariable=self.priv_var, show="*", width=66)

        self._build_fields()

        ttk.Button(self, text="Speichern", command=self._save).grid(row=4, column=0, columnspan=2, pady=5)
        ttk.Label(self, textvariable=self.status_var, foreground="blue").grid(row=5, column=0, columnspan=2, sticky="w")

    def _on_exchange_change(self, _event=None) -> None:
        self._build_fields()

    def _build_fields(self) -> None:
        for widget in (self.key_entry, self.secret_entry, self.wallet_entry, self.private_entry):
            widget.grid_forget()

        exch = self.exchange_var.get()
        if exch == "dYdX":
            ttk.Label(self, text="Wallet:").grid(row=1, column=0, sticky="w")
            self.wallet_entry.grid(row=1, column=1, padx=5)
            ttk.Label(self, text="Private Key:").grid(row=2, column=0, sticky="w")
            self.private_entry.grid(row=2, column=1, padx=5)
        else:
            ttk.Label(self, text="API Key:").grid(row=1, column=0, sticky="w")
            self.key_entry.grid(row=1, column=1, padx=5)
            ttk.Label(self, text="API Secret:").grid(row=2, column=0, sticky="w")
            self.secret_entry.grid(row=2, column=1, padx=5)

    def _save(self) -> None:
        exch = self.exchange_var.get()
        if exch == "dYdX":
            wallet = self.wallet_var.get().strip()
            pkey = self.priv_var.get().strip()
            ok, msg = check_exchange_credentials(exch, wallet=wallet, private_key=pkey)
            if not ok:
                self._err(msg)
                return
            self.cred_manager.set_credentials(wallet, pkey)
            SETTINGS["dydx_wallet"] = wallet
            SETTINGS["dydx_private_key"] = pkey
        else:
            key = self.key_var.get().strip()
            secret = self.secret_var.get().strip()
            if not key or not secret:
                self._err("API Key und Secret erforderlich")
                return
            ok, msg = check_exchange_credentials(exch, key=key, secret=secret)
            if not ok:
                self._err(msg)
                return
            self.cred_manager.set_credentials(key, secret)
            SETTINGS[f"{exch.lower()}_key"] = key
            SETTINGS[f"{exch.lower()}_secret"] = secret
        if self.log_callback:
            self.log_callback("🔑 Zugangsdaten gespeichert (nur RAM)")
            self.log_callback(msg)
        else:
            messagebox.showinfo("Status", msg)

        # Status für GUI anzeigen
        self.status_var.set("aktiv" if ok else f"Fehler: {msg}")

        # Sofortige Status-Prüfung auslösen
        if ok and self.monitor:
            try:
                self.monitor.force_check()
            except Exception:
                pass

    def _err(self, msg: str) -> None:
        if self.log_callback:
            self.log_callback(f"⚠️ {msg}")
        else:
            messagebox.showwarning("Fehler", msg)
        # Status aktualisieren
        self.status_var.set(f"Fehler: {msg}")
