# gui_model.py
"""Model holding GUI state variables and basic control helpers."""

from __future__ import annotations

import tkinter as tk
from typing import Optional


class GUIModel:
    """Container for Tkinter variables and runtime state."""

    def __init__(self, root: tk.Misc) -> None:
        # runtime flags
        self.running: bool = False
        self.force_exit: bool = False
        self.should_stop: bool = False
        self.live_pnl: float = 0.0
        self.total_pnl: float = 0.0
        self.wins: int = 0
        self.losses: int = 0

        # general options
        self.auto_apply_recommendations = tk.BooleanVar(master=root, value=False)
        self.auto_multiplier = tk.BooleanVar(master=root, value=False)

        # Auto Partial Close
        self.apc_enabled = tk.BooleanVar(master=root, value=True)
        self.apc_rate = tk.StringVar(master=root, value="25")
        self.apc_interval = tk.StringVar(master=root, value="60")
        self.apc_min_profit = tk.StringVar(master=root, value="20")

        # risk limits
        self.max_loss_enabled = tk.BooleanVar(master=root, value=True)
        self.max_loss_value = tk.StringVar(master=root, value="60")
        self.risk_trade_pct = tk.StringVar(master=root, value="3.0")
        self.max_drawdown_pct = tk.StringVar(master=root, value="15.0")
        self.cooldown_minutes = tk.StringVar(master=root, value="2")

        # trading mode
        self.live_trading = tk.BooleanVar(master=root, value=False)
        self.paper_mode = tk.BooleanVar(master=root, value=True)
        self.trading_mode = tk.StringVar(master=root, value="paper")

        # basic parameters
        self.multiplier_var = tk.StringVar(master=root, value="10")
        self.capital_var = tk.StringVar(master=root, value="2000")

        # strategy options
        self.andac_lookback = tk.StringVar(master=root, value="20")
        self.andac_puffer = tk.StringVar(master=root, value="10.0")
        self.andac_vol_mult = tk.StringVar(master=root, value="1.2")

        self.andac_opt_rsi_ema = tk.BooleanVar(master=root)
        self.andac_opt_safe_mode = tk.BooleanVar(master=root)
        self.andac_opt_engulf = tk.BooleanVar(master=root)
        self.andac_opt_engulf_bruch = tk.BooleanVar(master=root)
        self.andac_opt_engulf_big = tk.BooleanVar(master=root)
        self.andac_opt_confirm_delay = tk.BooleanVar(master=root)
        self.andac_opt_mtf_confirm = tk.BooleanVar(master=root)
        self.andac_opt_volumen_strong = tk.BooleanVar(master=root)
        self.andac_opt_session_filter = tk.BooleanVar(master=root)

        self.use_doji_blocker = tk.BooleanVar(master=root)

        # timing
        self.interval = tk.StringVar(master=root, value="1m")
        self.use_time_filter = tk.BooleanVar(master=root)
        self.time_start = tk.StringVar(master=root, value="08:00")
        self.time_end = tk.StringVar(master=root, value="18:00")
        self.require_closed_candles = tk.BooleanVar(master=root, value=True)
        self.cooldown_after_exit = tk.StringVar(master=root, value="120")

        # manual SL/TP
        self.manual_sl_var = tk.StringVar(master=root, value="")
        self.manual_tp_var = tk.StringVar(master=root, value="")
        self.sl_tp_auto_active = tk.BooleanVar(master=root, value=False)
        self.sl_tp_manual_active = tk.BooleanVar(master=root, value=False)
        self.sl_tp_status_var = tk.StringVar(master=root, value="")
        self.last_reason_var = tk.StringVar(master=root, value="–")

        # expert settings
        self.entry_cooldown_seconds = tk.StringVar(master=root, value="60")
        self.sl_tp_mode = tk.StringVar(master=root, value="adaptive")
        self.min_profit_usd = tk.StringVar(master=root, value="1")
        self.partial_close_trigger = tk.StringVar(master=root, value="50")
        self.fee_model = tk.StringVar(master=root, value="0.075")
        self.max_trades_per_hour = tk.StringVar(master=root, value="5")

        # connection status
        self.feed_ok: bool = False
        self.api_ok: bool = False
        self.websocket_active: bool = False

    # --- helper methods -------------------------------------------------
    def toggle_manual_sl_tp(self, sl: Optional[str], tp: Optional[str]) -> bool:
        """Enable manual SL/TP if both values are valid."""
        try:
            float(sl.replace(",", "."))
            float(tp.replace(",", "."))
        except Exception:
            self.sl_tp_manual_active.set(False)
            return False

        self.manual_sl_var.set(sl)
        self.manual_tp_var.set(tp)
        self.sl_tp_manual_active.set(True)
        self.sl_tp_auto_active.set(False)
        return True

    def activate_auto_sl_tp(self) -> None:
        """Switch SL/TP handling to automatic mode."""
        self.sl_tp_auto_active.set(True)
        self.sl_tp_manual_active.set(False)

    def set_auto_sl_status(self, ok: bool) -> None:
        self.sl_tp_auto_active.set(ok)
        if ok:
            self.sl_tp_manual_active.set(False)

    def set_manual_sl_status(self, ok: bool) -> None:
        self.sl_tp_manual_active.set(ok)
        if ok:
            self.sl_tp_auto_active.set(False)
