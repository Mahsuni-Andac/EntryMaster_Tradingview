# trading_gui_core.py

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import logging
from binance.client import Client

from .trading_gui_logic import TradingGUILogicMixin
from .api_credential_frame import APICredentialFrame, EXCHANGES
from .neon_status_panel import NeonStatusPanel
from api_key_manager import APICredentialManager
from status_events import StatusDispatcher

class TradingGUI(TradingGUILogicMixin):
    def __init__(self, root, cred_manager: APICredentialManager | None = None):
        self.root = root
        # Set window title to reflect the new project name
        self.root.title("🧞‍♂️ EntryMaster_Tradingview – Kapital-Safe Edition")

        # --- API-Zugangsdaten ---
        self.cred_manager = cred_manager or APICredentialManager()

        # --- Zustände & Live-Werte ---
        self.running = False
        self.force_exit = False
        self.live_pnl = 0.0

        self.auto_apply_recommendations = tk.BooleanVar(value=False)
        self.auto_multiplier = tk.BooleanVar(value=False)

        # --- APC & Verlustlimit ---
        self.apc_enabled = tk.BooleanVar(value=False)
        self.apc_rate = tk.StringVar(value="10")
        self.apc_interval = tk.StringVar(value="60")
        self.apc_min_profit = tk.StringVar(value="0")
        self.apc_status_label = None

        self.max_loss_enabled = tk.BooleanVar(value=True)
        self.max_loss_value = tk.StringVar(value="10")
        self.max_loss_status_label = None

        # --- Controls & Vars ---
        self.multiplier_entry = None
        self.capital_entry = None
        self.log_box = None
        self.auto_status_label = None
        self.live_trading = tk.BooleanVar(value=False)
        self.trading_mode = tk.StringVar(value="paper")
        self.mode_label = None

        self._init_variables()
        self._build_gui()
        self._init_neon_panel()
        self._collect_setting_vars()
        self._build_status_panel()
        StatusDispatcher.on_api_status(self.update_api_status)
        StatusDispatcher.on_feed_status(self.update_feed_status)

        # Binance REST client für Preisabfragen
        self.binance_client = Client()

        # MARKTDATEN-MONITOR starten
        self.market_interval_ms = 1000
        self._update_market_monitor()

        # Reduce overall window height by 10% after layout is built
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = int(self.root.winfo_height() * 0.9)
        self.root.geometry(f"{width}x{height}")

    # ---- Neon Status Panel -------------------------------------------
    def _init_neon_panel(self):
        self.neon_panel = NeonStatusPanel(self.root)
        self.neon_panel.frame.pack(side="right", fill="y", padx=(0, 5))

        mapping = {
            "api": ("API Status", None),
            "feed": ("Datenfeed", None),
            "apc": ("Auto Partial Close", self.apc_enabled),
            "loss": ("Verlustlimit", self.max_loss_enabled),
            "auto_rec": ("Auto Empfehlungen", self.auto_apply_recommendations),
            "auto_multi": ("Auto Multiplikator", self.auto_multiplier),
            "safe": ("Sicherheitsfilter", self.andac_opt_safe_mode),
            "vol": ("Volumenfilter", self.andac_opt_volumen_strong),
            "session": ("Session Filter", self.andac_opt_session_filter),
        }

        self._neon_vars = {}
        for key, (desc, var) in mapping.items():
            self.neon_panel.register(key, desc)
            if isinstance(var, tk.BooleanVar):
                self._neon_vars[key] = var
                var.trace_add("write", lambda *a, k=key, v=var: self._update_neon_var(k, v))
                self._update_neon_var(key, var)

    def _update_neon_var(self, key, var):
        color = "green" if var.get() else "blue"
        self.neon_panel.set_status(key, color)

    def _update_mode_label(self):
        if self.live_trading.get():
            text = "Live Trading"
            color = "red"
        else:
            text = "Paper Trading"
            color = "blue"
        if self.mode_label is not None:
            self.mode_label.config(text=text, foreground=color)

    def _on_mode_toggle(self):
        self.live_trading.set(self.trading_mode.get() == "live")
        self._update_mode_label()

    def _init_variables(self):
        self.multiplier_var = tk.StringVar(value="20")
        self.capital_var = tk.StringVar(value="1000")
        
        # --- Andac Entry-Master Optionen ---
        self.andac_lookback = tk.StringVar(value="20")
        self.andac_puffer = tk.StringVar(value="10.0")
        self.andac_vol_mult = tk.StringVar(value="1.2")

        self.andac_opt_rsi_ema = tk.BooleanVar()
        self.andac_opt_safe_mode = tk.BooleanVar()
        self.andac_opt_engulf = tk.BooleanVar()
        self.andac_opt_engulf_bruch = tk.BooleanVar()
        self.andac_opt_engulf_big = tk.BooleanVar()
        self.andac_opt_confirm_delay = tk.BooleanVar()
        self.andac_opt_mtf_confirm = tk.BooleanVar()
        self.andac_opt_volumen_strong = tk.BooleanVar()
        self.andac_opt_session_filter = tk.BooleanVar()

        # Zusätzliche Filter
        self.use_doji_blocker = tk.BooleanVar()

        self.interval = tk.StringVar(value="1m")
        self.use_time_filter = tk.BooleanVar()
        self.time_start = tk.StringVar(value="08:00")
        self.time_end = tk.StringVar(value="18:00")

        # Empfehlungslayouts (optional)
        self.rsi_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.volume_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.volboost_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.ema_rec_label = ttk.Label(self.root, text="", foreground="green")
        
        self.bigcandle_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.breakout_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.rsi_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.volume_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.volboost_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.ema_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.doji_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.engulfing_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.bigcandle_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.breakout_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.safemode_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.engulf_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.cool_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.safe_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.auto_status_label = None

        # Statusanzeigen für API & Datenfeed
        self.api_status_var = tk.StringVar(value="API ❌")
        self.feed_status_var = tk.StringVar(value="Feed ❌")
        self.api_status_label = None
        self.feed_status_label = None
        # Track current connection states for the watchdog
        self.feed_ok = False
        self.api_ok = False

        # Statusvariablen je Exchange
        self.exchange_status_vars = {ex: tk.StringVar(value="⚪") for ex in EXCHANGES}
        self.exchange_status_labels = {}
        self.exchange_status_cache = {}

    def _build_gui(self):
        # wrapper for main content to allow side panels
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side="left", fill="both", expand=True)

        # --- Oberer Info-Bereich ---
        top_info = ttk.Frame(self.main_frame)
        top_info.pack(pady=5)
        self._build_api_credentials(top_info)
        self.capital_value = ttk.Label(top_info, text="💰 Kapital: $0", foreground="green", font=("Arial", 11, "bold"))
        self.capital_value.pack(side="left", padx=10)
        # Sparkonto/Gewinn-Anzeige entfernt
        self.pnl_value = ttk.Label(top_info, text="📉 PnL: $0", foreground="black", font=("Arial", 11, "bold"))
        self.pnl_value.pack(side="left", padx=10)

        self.api_status_label = ttk.Label(top_info, textvariable=self.api_status_var, foreground="red", font=("Arial", 11, "bold"))
        self.api_status_label.pack(side="left", padx=10)
        self.feed_status_label = ttk.Label(top_info, textvariable=self.feed_status_var, foreground="red", font=("Arial", 11, "bold"))
        self.feed_status_label.pack(side="left", padx=10)
        self.mode_label = ttk.Label(top_info, text="Paper Trading", foreground="blue", font=("Arial", 11, "bold"))
        self.mode_label.pack(side="left", padx=10)

        mode_frame = ttk.Frame(top_info)
        mode_frame.pack(side="left")
        ttk.Radiobutton(
            mode_frame,
            text="Paper Trading",
            variable=self.trading_mode,
            value="paper",
            command=self._on_mode_toggle,
        ).pack(side="left")
        ttk.Radiobutton(
            mode_frame,
            text="Live Trading",
            variable=self.trading_mode,
            value="live",
            command=self._on_mode_toggle,
        ).pack(side="left")
        self._on_mode_toggle()

        # --- Hauptcontainer ---
        container = ttk.Frame(self.main_frame)
        container.pack(padx=10, pady=5)
        risk = ttk.Frame(container)
        left = ttk.Frame(container)
        right = ttk.Frame(container)
        middle = ttk.Frame(container)
        extra = ttk.Frame(container)
        andac = ttk.Frame(container)

        # Neue Spalte für Risikomanagement ganz links
        risk.grid(row=0, column=0, padx=10, sticky="nw")
        left.grid(row=0, column=1, padx=10, sticky="ne")
        right.grid(row=0, column=2, padx=10, sticky="ne")
        middle.grid(row=0, column=3, padx=10, sticky="n")
        extra.grid(row=0, column=4, padx=10, sticky="ne")
        andac.grid(row=0, column=5, padx=10, sticky="ne")

        # --- Options-Überschrift über dem Intervall ---
        ttk.Label(middle, text="⚙️ Optionen", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=6, pady=(0, 5), sticky="w")

        # --- Middle ---
        ema_row = ttk.Frame(middle)
        ema_row.grid(row=1, column=0, columnspan=6, pady=(0, 8), sticky="w")
        ttk.Label(ema_row, text="Intervall:").pack(side="left")
        ttk.Combobox(
            ema_row,
            textvariable=self.interval,
            values=[
                "1m", "3m", "5m", "10m", "15m", "30m", "45m",
                "1h", "2h", "3h", "4h", "6h", "8h", "12h",
                "1d", "2d", "3d", "1w"
            ],
            width=6
        ).pack(side="left", padx=(4,0))

        multi_row = ttk.Frame(middle)
        multi_row.grid(row=2, column=0, columnspan=6, pady=(0, 8), sticky="w")
        ttk.Label(multi_row, text="Multiplikator:").pack(side="left")
        self.multiplier_entry = ttk.Entry(multi_row, width=8, textvariable=self.multiplier_var)
        self.multiplier_entry.pack(side="left", padx=(4,8))
        ttk.Checkbutton(multi_row, text="Auto", variable=self.auto_multiplier).pack(side="left", padx=(0,8))
        ttk.Label(multi_row, text="Einsatz ($):").pack(side="left", padx=(6,0))
        self.capital_entry = ttk.Entry(multi_row, width=8, textvariable=self.capital_var)
        self.capital_entry.pack(side="left", padx=(4,0))

        time_filter_row = ttk.Frame(middle)
        time_filter_row.grid(row=3, column=0, columnspan=6, pady=(0, 8), sticky="w")
        ttk.Checkbutton(time_filter_row, text="Uhrzeit-Filter", variable=self.use_time_filter).pack(side="left")

        self.time_filters = []
        for i in range(4):
            row = 4 + (i // 2)
            col = i % 2
            label = ttk.Label(middle, text=f"Zeitfenster {i+1}")
            label.grid(row=row*2, column=col, padx=5, pady=(5, 0), sticky="w")
            start = tk.StringVar(value="08:00")
            end = tk.StringVar(value="18:00")
            ttk.Entry(middle, textvariable=start, width=8).grid(row=row*2+1, column=col*2, padx=5)
            ttk.Entry(middle, textvariable=end, width=8).grid(row=row*2+1, column=col*2+1, padx=5)
            self.time_filters.append((start, end))

        # --- Risikomanagement-Spalte ---
        ttk.Label(risk, text="⚠️ Risikomanagement", font=("Arial", 11, "bold")).grid(row=0, column=0, pady=(0, 5), sticky="w")

        apc_frame = ttk.LabelFrame(risk, text="Auto Partial Close")
        apc_frame.grid(row=1, column=0, padx=5, sticky="nw")
        ttk.Checkbutton(apc_frame, text="Aktivieren", variable=self.apc_enabled).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(apc_frame, text="Teilverkaufsrate [%/Intervall]:").grid(row=1, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_rate, width=6).grid(row=1, column=1)
        ttk.Label(apc_frame, text="Intervall [Sekunden]:").grid(row=2, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_interval, width=6).grid(row=2, column=1)
        ttk.Label(apc_frame, text="Mindestgewinn [$]:").grid(row=3, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_min_profit, width=6).grid(row=3, column=1)
        self.apc_status_label = ttk.Label(apc_frame, text="", foreground="blue")
        self.apc_status_label.grid(row=4, column=0, columnspan=2, sticky="w")

        loss_frame = ttk.LabelFrame(risk, text="Verlust-Limit / Auto-Pause")
        loss_frame.grid(row=2, column=0, padx=5, pady=(10, 0), sticky="nw")
        ttk.Checkbutton(loss_frame, text="Aktivieren", variable=self.max_loss_enabled).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(loss_frame, text="Maximaler Verlust bis Pause [$]:").grid(row=1, column=0, sticky="w")
        ttk.Entry(loss_frame, textvariable=self.max_loss_value, width=8).grid(row=1, column=1)
        self.max_loss_status_label = ttk.Label(loss_frame, text="", foreground="red")
        self.max_loss_status_label.grid(row=3, column=0, columnspan=2, sticky="w")

        self._build_andac_options(andac)
        self._build_controls(self.main_frame)



    def _build_andac_options(self, parent):
        ttk.Label(parent, text="🤑 Entry-Master 🚀", font=("Arial", 11, "bold")).pack(pady=(0, 5))
        # Zwei-Spalten-Layout: Links Checkboxen, rechts Parameter
        options_frame = ttk.Frame(parent)
        options_frame.pack()
        left_col = ttk.Frame(options_frame)
        right_col = ttk.Frame(options_frame)
        left_col.pack(side="left", padx=5, anchor="n")
        right_col.pack(side="left", padx=5, anchor="n")

        # Checkbox-Optionen (linke Spalte)
        for text, var in [
            ("RSI/EMA", self.andac_opt_rsi_ema),
            ("🛡 Sicherheitsfilter", self.andac_opt_safe_mode),
            ("Engulfing", self.andac_opt_engulf),
            ("Engulfing + Breakout", self.andac_opt_engulf_bruch),
            ("Engulfing > ATR", self.andac_opt_engulf_big),
            ("Bestätigungskerze", self.andac_opt_confirm_delay),
            ("MTF Bestätigung", self.andac_opt_mtf_confirm),
            ("Starkes Volumen", self.andac_opt_volumen_strong),
            ("EU/NY Session", self.andac_opt_session_filter),
        ]:
            ttk.Checkbutton(left_col, text=text, variable=var).pack(anchor="w")

        # Parameter-Eingaben (rechte Spalte)
        self._add_entry_group(right_col, "Lookback", [self.andac_lookback])
        self._add_entry_group(right_col, "Toleranz", [self.andac_puffer])
        self._add_entry_group(right_col, "Volumen-Faktor", [self.andac_vol_mult])

    def _build_controls(self, root):
        button_frame = ttk.Frame(root)
        button_frame.pack(pady=10, fill="x")  # Vermeide Pack und Grid gleichzeitig!

        # Buttons in einem Grid platzieren
        ttk.Button(button_frame, text="▶️ Bot starten", command=self.start_bot).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="⛔ Trade abbrechen", command=self.emergency_flat_position).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="❗️ Notausstieg", command=self.emergency_exit).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="🛑 Alles stoppen & sichern", command=self.stop_and_reset).grid(row=0, column=3, padx=5)

        ttk.Checkbutton(
            button_frame,
            text="🔁 Auto-Empfehlungen",
            variable=self.auto_apply_recommendations,
            command=self.update_auto_status,
        ).grid(row=1, column=0, padx=5)
        ttk.Button(button_frame, text="✅ Empfehlungen übernehmen", command=self.apply_recommendations).grid(row=1, column=1, padx=5)
        ttk.Button(button_frame, text="🧹 Alles deaktivieren", command=self.disable_all_filters).grid(row=1, column=2, padx=5)
        ttk.Button(button_frame, text="💾 Einstellungen speichern", command=self.save_to_file).grid(row=1, column=3, padx=5)
        ttk.Button(button_frame, text="⏏️ Einstellungen laden", command=self.load_from_file).grid(row=1, column=4, padx=5)

        # Auto-Status-Label weiter rechts platzieren
        self.auto_status_label = ttk.Label(button_frame, font=("Arial", 10, "bold"), foreground="green")
        self.auto_status_label.grid(row=2, column=0, columnspan=5, pady=(5, 0), padx=10, sticky="w")

        # Logbox unterhalb der Buttons
        self.log_box = tk.Text(root, height=13, width=85, wrap="word", bg="#f9f9f9", relief="sunken", borderwidth=2)
        self.log_box.pack(pady=12)

    def stop_and_reset(self):
        """Stoppt den Bot, ohne die Konfiguration zurückzusetzen."""
        self.force_exit = True
        self.running = False
        self.log_event("🧹 Bot gestoppt – Keine Rücksetzung der Konfiguration vorgenommen.")

    def _add_checkbox_entry(self, parent, label, var, entries=[]):
        ttk.Checkbutton(parent, text=label, variable=var).pack(anchor="w")
        for entry_var in entries:
            ttk.Entry(parent, textvariable=entry_var, width=6).pack(anchor="w")

    def _add_entry_group(self, parent, label, entries):
        ttk.Label(parent, text=label).pack()
        for var in entries:
            ttk.Entry(parent, textvariable=var).pack()

    def _build_api_credentials(self, parent):
        self.api_frame = APICredentialFrame(
            parent,
            self.cred_manager,
            log_callback=self.log_event,
            select_callback=self._on_exchange_select,
        )
        self.api_frame.pack(pady=(0, 10), fill="x")
        for exch in EXCHANGES:
            self.exchange_status_vars[exch] = self.api_frame.status_vars[exch]
            self.exchange_status_labels[exch] = self.api_frame.status_labels[exch]

    def _on_exchange_select(self, exch: str) -> None:
        if hasattr(self, "on_exchange_select"):
            self.on_exchange_select(exch)


    # ---- Status Panel -------------------------------------------------
    def _collect_setting_vars(self):
        """Collect all Tk variables for status tracking."""
        self.setting_vars = {
            name: var
            for name, var in vars(self).items()
            if isinstance(var, (tk.BooleanVar, tk.StringVar))
        }
        if hasattr(self, "api_frame"):
            for ex, data in self.api_frame.vars.items():
                for key, var in data.items():
                    if isinstance(var, tk.Variable):
                        self.setting_vars[f"api_{ex}_{key}"] = var
            for ex, var in self.api_frame.status_vars.items():
                self.setting_vars[f"api_{ex}_status"] = var
        if hasattr(self, "time_filters"):
            for idx, (start, end) in enumerate(self.time_filters, start=1):
                self.setting_vars[f"time_filter_{idx}_start"] = start
                self.setting_vars[f"time_filter_{idx}_end"] = end

    def _build_status_panel(self):
        """Create panel showing if settings are active in the backend."""
        self.backend_settings = {}
        self.status_labels = {}
        self.status_rows = {}
        frame = ttk.LabelFrame(self.root, text="Wirksamkeitsstatus")
        frame.pack(padx=10, pady=5, fill="both", expand=True)

        # Canvas für Scrollfunktion
        canvas = tk.Canvas(frame, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_config(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            if inner.winfo_reqheight() > canvas.winfo_height():
                if not scrollbar.winfo_ismapped():
                    scrollbar.pack(side="right", fill="y")
            else:
                if scrollbar.winfo_ismapped():
                    scrollbar.pack_forget()

        inner.bind("<Configure>", _on_config)
        self.root.bind("<Configure>", _on_config)

        self.all_ok_label = ttk.Label(inner, text="", foreground="green")
        self.all_ok_label.grid(row=0, column=0, sticky="w")
        row_index = 1
        for name, var in sorted(self.setting_vars.items()):
            row = ttk.Frame(inner)
            row.grid(row=row_index, column=0, columnspan=2, sticky="w")
            ttk.Label(row, text=name).pack(side="left")
            lbl = ttk.Label(row, text="", foreground="red")
            lbl.pack(side="left", padx=5)
            self.status_rows[name] = row
            self.status_labels[name] = lbl
            var.trace_add("write", lambda *a, n=name, v=var: self.update_setting_status(n, v))
            self.update_setting_status(name, var)
            row_index += 1

        _on_config()
        self.root.after(1000, self.update_all_status_labels)
        self._update_all_ok_label()

    def update_setting_status(self, name, var):
        """Verify and display the activation state of a setting.

        Bei ungültigen Werten wird der Fehler angezeigt und das
        Backend-Setting nicht überschrieben.
        """
        try:
            value = var.get()
            parsed = value
            if isinstance(var, tk.BooleanVar):
                parsed = bool(value)
            elif name.startswith("time_filter") or name in {"time_start", "time_end"}:
                datetime.strptime(value, "%H:%M")
            elif isinstance(value, str) and value.replace(".", "", 1).isdigit():
                parsed = float(value) if "." in value else int(value)

            current = self.backend_settings.get(name)
            if parsed != current:
                self.backend_settings[name] = parsed
            active = self.backend_settings.get(name) == parsed
            row = self.status_rows[name]
            label = self.status_labels[name]
            if active:
                row.grid_remove()
            else:
                label.config(text="inaktiv", foreground="red")
                if not row.winfo_ismapped():
                    row.grid()
                self.log_event(f"⚠️ {name} greift nicht")
        except Exception as e:
            row = self.status_rows[name]
            self.status_labels[name].config(text=f"Fehler: {e}", foreground="orange")
            if not row.winfo_ismapped():
                row.grid()
            self.log_event(f"{name} Fehler: {e}")
        self._update_all_ok_label()

    def update_all_status_labels(self):
        for name, var in self.setting_vars.items():
            self.update_setting_status(name, var)
        self.root.after(1000, self.update_all_status_labels)
        self._update_all_ok_label()

    def _update_all_ok_label(self):
        any_visible = any(row.winfo_ismapped() for row in self.status_rows.values())
        if any_visible:
            if self.all_ok_label.winfo_ismapped():
                self.all_ok_label.grid_remove()
        else:
            self.all_ok_label.config(text="✅ Alle Systeme laufen fehlerfrei")
            if not self.all_ok_label.winfo_ismapped():
                self.all_ok_label.grid()

    # MARKTDATEN-MONITOR -------------------------------------------------
    def _update_market_monitor(self) -> None:
        """Fetch Binance spot price and update mini terminal."""
        from config import SETTINGS

        symbol = SETTINGS.get("symbol", "BTCUSDT")

        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
        except Exception:
            price = None

        stamp = datetime.now().strftime("%H:%M:%S")
        line = (
            f"{symbol.replace('_','')}: {price:.2f} ({stamp})" if price is not None else f"{symbol}: ❌ ({stamp})"
        )
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "log_price"):
            self.api_frame.log_price(line, error=price is None)
        if price is not None:
            self.update_feed_status(True)
        else:
            self.update_feed_status(False, "Keine Marktdaten – bitte prüfen")

        self.root.after(self.market_interval_ms, self._update_market_monitor)


