import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict

from api_key_manager import APICredentialManager
from credential_checker import check_exchange_credentials
from status_events import StatusDispatcher
from config import SETTINGS
from binance.client import Client

# Order of exchanges in the selection box
EXCHANGES = ["BitMEX"]

class APICredentialFrame(ttk.LabelFrame):
    """GUI frame for managing multiple exchange credentials."""

    def __init__(self, master: tk.Misc, cred_manager: APICredentialManager, log_callback=None, select_callback=None) -> None:
        super().__init__(master, text="Exchange API")
        self.cred_manager = cred_manager
        self.log_callback = log_callback
        self.select_callback = select_callback

        # no exchange active until the user selects one
        self.active_exchange = tk.StringVar(value="")

        self.vars: Dict[str, Dict[str, tk.Variable]] = {}
        self.status_vars: Dict[str, tk.StringVar] = {}
        self.status_labels: Dict[str, ttk.Label] = {}

        self.data_source_mode = tk.StringVar(value=SETTINGS.get("data_source_mode", "rest"))

        ttk.Label(self, text="Trading-Exchange:").grid(row=0, column=0, sticky="w")
        box = ttk.Combobox(self, state="readonly", values=EXCHANGES, textvariable=self.active_exchange, width=10)
        box.grid(row=0, column=1, sticky="w")
        box.bind("<<ComboboxSelected>>", lambda _e: self._on_select())

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
        ttk.Label(control_row, text="Marktdatenquelle (Binance):").pack(side="left", padx=(10, 2))
        ttk.OptionMenu(
            control_row,
            self.data_source_mode,
            self.data_source_mode.get(),
            "rest",
            "websocket",
            "auto",
            command=lambda v: self._on_source_change(v),
        ).pack(side="left")

        self.market_status = tk.StringVar(value="")

        status_row = ttk.Frame(self)
        status_row.grid(row=start_row + len(EXCHANGES) + 1, column=0, columnspan=4, sticky="w")

        self.market_status_label = ttk.Label(status_row, textvariable=self.market_status, foreground="red")
        self.market_status_label.pack(side="left")

        self.system_status = tk.StringVar(value="")
        self.system_status_label = ttk.Label(status_row, textvariable=self.system_status, foreground="green")
        self.system_status_label.pack(side="left", padx=(10, 0))

        # Anzeige, ob Daten via WebSocket oder REST empfangen werden
        self.feed_mode = tk.StringVar(value="")
        self.feed_mode_label = ttk.Label(status_row, textvariable=self.feed_mode, foreground="green")
        self.feed_mode_label.pack(side="left", padx=(10, 0))

        # disable all fields until user actively chooses an exchange
        self._select_exchange("")

        # Mini price monitor
        term_frame = tk.Frame(self, bg="black")
        term_frame.grid(row=0, column=4, rowspan=len(EXCHANGES)+1, padx=5, sticky="ne")
        self.price_terminal = tk.Text(term_frame, height=6, width=24, bg="black", fg="green", state="disabled")
        self.price_terminal.pack()

        self.check_market_feed()

    # ------------------------------------------------------------------
    def _select_exchange(self, exch: str) -> None:
        """Enable entry fields for *exch* and reset others."""
        for name in EXCHANGES:
            data = self.vars[name]
            state = "normal" if name == exch else "disabled"
            data["entry1"].config(state=state)
            data["entry2"].config(state=state)
            if name != exch:
                self.status_vars[name].set("⚪")
                self.status_labels[name].config(foreground="grey")

    def _on_select(self) -> None:
        exch = self.active_exchange.get()
        self._select_exchange(exch)
        # limit credential checks to the selected exchange
        from config import SETTINGS
        SETTINGS["enabled_exchanges"] = [exch.lower()] if exch else []
        SETTINGS.pop("trading_backend", None)
        if self.select_callback:
            self.select_callback(exch)
        self.check_market_feed()

    def _on_source_change(self, mode: str) -> None:
        from data_provider import switch_feed_source

        SETTINGS["data_source_mode"] = mode
        symbol = SETTINGS.get("symbol", "BTCUSDT")

        switch_feed_source(mode, symbol)

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
        try:
            Client().get_symbol_ticker(symbol="BTCUSDT")
            ok = True
        except Exception:
            ok = False
        self.update_market_status(ok)

    # ------------------------------------------------------------------
    def _save(self) -> None:
        exch = self.active_exchange.get()
        if not exch:
            if self.log_callback:
                self.log_callback("Keine Exchange gewählt")
            else:
                messagebox.showinfo("Status", "Bitte Exchange wählen")
            return
        data = self.vars[exch]
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
        SETTINGS["data_source_mode"] = self.data_source_mode.get()

        self.status_vars[exch].set("✅" if ok else "❌")
        self.status_labels[exch].config(foreground="green" if ok else "red")
        if self.log_callback:
            self.log_callback(msg)
        else:
            messagebox.showinfo("Status", msg)

        if ok:
            SETTINGS["trading_backend"] = exch.lower()
            SETTINGS["enabled_exchanges"] = [exch.lower()]
        else:
            SETTINGS.pop("trading_backend", None)
            SETTINGS["enabled_exchanges"] = [exch.lower()]
        StatusDispatcher.dispatch("api", ok, None if ok else "Keine API aktiv")
        self.check_market_feed()

