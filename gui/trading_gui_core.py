# trading_gui_core.py

import tkinter as tk
from tkinter import ttk
from .trading_gui_logic import TradingGUILogicMixin
from .api_credential_frame import APICredentialFrame
from api_key_manager import APICredentialManager

class TradingGUI(TradingGUILogicMixin):
    def __init__(self, root, cred_manager: APICredentialManager | None = None):
        self.root = root
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

        self._init_variables()
        self._build_gui()

    def _init_variables(self):
        self.multiplier_var = tk.StringVar(value="20")
        self.capital_var = tk.StringVar(value="1000")
        
        self.interval = tk.StringVar(value="1m")
        self.sl_mode = tk.StringVar(value="atr")
        self.stop_loss_atr_multiplier = tk.StringVar(value="0.5")
        self.take_profit_atr_multiplier = tk.StringVar(value="1.5")
        self.sl_fix = tk.StringVar(value="20")
        self.tp_fix = tk.StringVar(value="30")
        self.sl_tp_min_distance = tk.StringVar(value="5")

        self.use_safe_mode = tk.BooleanVar(value=True)

        # Keine Empfehlungslayouts notwendig
        self.auto_status_label = None

    def _build_gui(self):
        # --- Oberer Info-Bereich ---
        top_info = ttk.Frame(self.root)
        top_info.pack(pady=5)
        self._build_api_credentials(top_info)
        self.capital_value = ttk.Label(top_info, text="💰 Kapital: $0", foreground="green", font=("Arial", 11, "bold"))
        self.capital_value.pack(side="left", padx=10)
        # Sparkonto/Gewinn-Anzeige entfernt
        self.pnl_value = ttk.Label(top_info, text="📉 PnL: $0", foreground="black", font=("Arial", 11, "bold"))
        self.pnl_value.pack(side="left", padx=10)

        # --- Hauptcontainer ---
        container = ttk.Frame(self.root)
        container.pack(padx=10, pady=5)
        left = ttk.Frame(container)
        right = ttk.Frame(container)
        middle = ttk.Frame(container)
        extra = ttk.Frame(container)
        left.grid(row=0, column=0, padx=10, sticky="nw")
        right.grid(row=0, column=1, padx=10, sticky="ne")
        middle.grid(row=0, column=2, padx=10, sticky="n")
        extra.grid(row=0, column=3, padx=10, sticky="ne")

        # --- Rechts: Optionen ---
        ttk.Label(extra, text="⚙️ Optionen", font=("Arial", 11, "bold")).pack(pady=(0, 5))
        ttk.Label(extra, text="SL/TP Modus:").pack()
        ttk.Combobox(extra, textvariable=self.sl_mode, values=["atr", "fix"]).pack()
        self._add_entry_group(extra, "SL/TP Mindestabstand", [self.sl_tp_min_distance])
        ttk.Checkbutton(extra, text="🛡 Sicherer Modus", variable=self.use_safe_mode).pack(anchor="w")

        # --- Middle ---
        ttk.Label(middle, text="Intervall:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            middle,
            textvariable=self.interval,
            values=[
                "1m", "3m", "5m", "10m", "15m", "30m", "45m",
                "1h", "2h", "3h", "4h", "6h", "8h", "12h",
                "1d", "2d", "3d", "1w"
            ],
            width=6
        ).grid(row=0, column=1, padx=(4,0))

        multi_row = ttk.Frame(middle)
        multi_row.grid(row=1, column=0, columnspan=6, pady=(0, 8), sticky="w")
        ttk.Label(multi_row, text="Multiplikator:").pack(side="left")
        self.multiplier_entry = ttk.Entry(multi_row, width=8, textvariable=self.multiplier_var)
        self.multiplier_entry.pack(side="left", padx=(4,8))
        ttk.Checkbutton(multi_row, text="Auto", variable=self.auto_multiplier).pack(side="left", padx=(0,8))
        ttk.Label(multi_row, text="Einsatz ($):").pack(side="left", padx=(6,0))
        self.capital_entry = ttk.Entry(multi_row, width=8, textvariable=self.capital_var)
        self.capital_entry.pack(side="left", padx=(4,0))



        self._build_signalfilter(left)
        self._build_controls(self.root)

        # --- Unten: Auto Partial Close und Verlust-Limit ---
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(pady=10)

        apc_frame = ttk.LabelFrame(bottom_frame, text="Auto Partial Close")
        apc_frame.grid(row=0, column=0, padx=15, sticky="n")
        ttk.Checkbutton(apc_frame, text="Aktivieren", variable=self.apc_enabled).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(apc_frame, text="Teilverkaufsrate [%/Intervall]:").grid(row=1, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_rate, width=6).grid(row=1, column=1)
        ttk.Label(apc_frame, text="Intervall [Sekunden]:").grid(row=2, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_interval, width=6).grid(row=2, column=1)
        ttk.Label(apc_frame, text="Mindestgewinn [$]:").grid(row=3, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_min_profit, width=6).grid(row=3, column=1)
        self.apc_status_label = ttk.Label(apc_frame, text="", foreground="blue")
        self.apc_status_label.grid(row=4, column=0, columnspan=2, sticky="w")

        loss_frame = ttk.LabelFrame(bottom_frame, text="Verlust-Limit / Auto-Pause")
        loss_frame.grid(row=0, column=1, padx=15, sticky="n")
        ttk.Checkbutton(loss_frame, text="Aktivieren", variable=self.max_loss_enabled).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(loss_frame, text="Maximaler Verlust bis Pause [$]:").grid(row=1, column=0, sticky="w")
        ttk.Entry(loss_frame, textvariable=self.max_loss_value, width=8).grid(row=1, column=1)
        self.max_loss_status_label = ttk.Label(loss_frame, text="", foreground="red")
        self.max_loss_status_label.grid(row=3, column=0, columnspan=2, sticky="w")


    def _build_signalfilter(self, parent):
        ttk.Label(parent, text="Andac Entry-Master", font=("Arial", 11, "bold")).pack(pady=(0, 5))

    def _build_strukturfilter(self, parent):
        pass

    def _build_controls(self, root):
        button_frame = ttk.Frame(root)
        button_frame.pack(pady=10, fill="x")  # Vermeide Pack und Grid gleichzeitig!

        # Buttons in einem Grid platzieren
        ttk.Button(button_frame, text="▶️ Bot starten", command=self.start_bot).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="⛔ Trade abbrechen", command=self.emergency_flat_position).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="❗️ Notausstieg", command=self.emergency_exit).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="🛑 Alles stoppen & sichern", command=self.stop_and_reset).grid(row=0, column=3, padx=5)

        ttk.Button(button_frame, text="💾 Einstellungen speichern", command=self.save_to_file).grid(row=1, column=0, padx=5)
        ttk.Button(button_frame, text="⏏️ Einstellungen laden", command=self.load_from_file).grid(row=1, column=1, padx=5)

        # Auto-Status-Label weiter rechts platzieren
        self.auto_status_label = ttk.Label(button_frame, font=("Arial", 10, "bold"), foreground="green")
        self.auto_status_label.grid(row=2, column=0, columnspan=5, pady=(5, 0), padx=10, sticky="w")

        # Logbox unterhalb der Buttons
        self.log_box = tk.Text(root, height=14, width=85, wrap="word", bg="#f9f9f9", relief="sunken", borderwidth=2)
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
        api_frame = APICredentialFrame(parent, self.cred_manager, log_callback=self.log_event)
        api_frame.pack(pady=(0, 10), fill="x")


