# risk_manager.py

from __future__ import annotations

from typing import Optional

from console_status import print_warning, print_stop_banner


class RiskManager:

    def __init__(self, gui, start_capital: Optional[float] = None) -> None:
        self.gui = gui
        self.start_capital: float = start_capital or 0.0
        self.current_capital: float = start_capital or 0.0
        self.highest_capital: float = start_capital or 0.0
        self.running_loss: float = 0.0
        self.loss_count: int = 0

        # configurable thresholds
        self.max_loss: float | None = None
        self.max_drawdown: float | None = None
        self.max_trades: int | None = None
        self.trade_count: int = 0

    def configure(self, **kwargs) -> None:
        """Update risk thresholds dynamically."""
        if "max_loss" in kwargs:
            self.max_loss = kwargs["max_loss"]
        if "max_drawdown" in kwargs:
            self.max_drawdown = kwargs["max_drawdown"]
        if "max_trades" in kwargs:
            self.max_trades = kwargs["max_trades"]

    def update_loss(self, realized_pnl: float) -> None:
        self.running_loss += realized_pnl
        if realized_pnl < 0:
            self.loss_count += 1
        else:
            self.loss_count = 0

    def update_capital(self, capital: float) -> None:
        self.current_capital = capital
        self.highest_capital = max(self.highest_capital, capital)

    def check_loss_limit(self) -> bool:
        """Return True if the loss limit is exceeded."""
        limit = self.max_loss
        if limit is None:
            enabled_var = getattr(self.gui, "max_loss_enabled", None)
            if not (hasattr(enabled_var, "get") and enabled_var.get()):
                return False
            try:
                limit = float(self.gui.max_loss_value.get())
            except Exception:
                return False

        if limit <= 0:
            return False

        absolute_loss = self.start_capital - self.current_capital
        if absolute_loss >= limit or self.running_loss <= -abs(limit):
            msg = f"Handel gestoppt: Max. Verlust erreicht ({absolute_loss:.2f}$)"
            if hasattr(self.gui, "max_loss_status_label"):
                self.gui.max_loss_status_label.config(text=f"🛑 {msg}", foreground="red")
            if hasattr(self.gui, "log_event"):
                self.gui.log_event(f"🛑 {msg}")
            print_warning(msg, warn_key="max_loss")
            print_stop_banner(msg)
            self.gui.running = False
            return True
        return False

    def check_drawdown_limit(self) -> bool:
        limit = self.max_drawdown
        if limit is None:
            enabled_var = getattr(self.gui, "max_drawdown_enabled", None)
            if not (hasattr(enabled_var, "get") and enabled_var.get()):
                return False
            try:
                limit = float(self.gui.max_drawdown_value.get())
            except Exception:
                return False

        drawdown = self.highest_capital - self.current_capital
        if drawdown >= abs(limit):
            msg = f"Handel gestoppt: Drawdown-Limit erreicht ({drawdown:.2f}$)"
            if hasattr(self.gui, "max_drawdown_status_label"):
                self.gui.max_drawdown_status_label.config(text=f"🛑 {msg}", foreground="red")
            if hasattr(self.gui, "log_event"):
                self.gui.log_event(f"🛑 {msg}")
            print_warning(msg, warn_key="max_drawdown")
            print_stop_banner(msg)
            self.gui.running = False
            return True
        return False

    def check_trade_limit(self) -> bool:
        """Return True if the configured trade count limit is reached."""
        if self.max_trades is None:
            return False
        if self.trade_count >= self.max_trades:
            msg = f"Handel gestoppt: Max. Trades erreicht ({self.trade_count})"
            if hasattr(self.gui, "log_event"):
                self.gui.log_event(f"🛑 {msg}")
            print_stop_banner(msg)
            self.gui.running = False
            return True
        return False

    def increment_trades(self) -> None:
        self.trade_count += 1

    def reset_loss(self) -> None:
        self.running_loss = 0.0
        self.loss_count = 0
        self.highest_capital = self.current_capital
        if hasattr(self.gui, "max_loss_status_label"):
            self.gui.max_loss_status_label.config(text="")
        if hasattr(self.gui, "max_drawdown_status_label"):
            self.gui.max_drawdown_status_label.config(text="")

    def handle_consecutive_loss(self, threshold: int = 3, cooldown_min: int = 30) -> None:
        if self.loss_count >= threshold:
            print(f"🚨 {self.loss_count} Verluste in Folge! (Extra-Cooldown wäre hier möglich)")
            self.loss_count = 0


