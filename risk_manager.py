# risk_manager.py

from __future__ import annotations

from typing import Optional
import logging

logger = logging.getLogger(__name__)

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
        self.max_risk_pct: float | None = None
        self.drawdown_pct: float | None = None

        # new risk parameters
        self.max_risk: float = 3.0
        self.drawdown_limit: float = 15.0
        self.initial_capital: float = self.start_capital
        self.total_loss: float = 0.0

    def configure(self, **kwargs) -> None:
        """Update risk thresholds dynamically."""
        if "max_loss" in kwargs:
            self.max_loss = kwargs["max_loss"]
        if "max_drawdown" in kwargs:
            self.max_drawdown = kwargs["max_drawdown"]
        if "max_trades" in kwargs:
            self.max_trades = kwargs["max_trades"]
        if "risk_per_trade" in kwargs:
            self.max_risk_pct = kwargs["risk_per_trade"]
        if "drawdown_pct" in kwargs:
            self.drawdown_pct = kwargs["drawdown_pct"]

    def update_loss(self, realized_pnl: float) -> None:
        self.running_loss += realized_pnl
        if realized_pnl < 0:
            self.loss_count += 1
            self.register_loss(-realized_pnl)
            limit = self.max_risk_pct
            if limit is None:
                try:
                    limit = float(self.gui.risk_trade_pct.get())
                except Exception:
                    limit = None
            if limit:
                max_risk = self.current_capital * limit / 100
                if abs(realized_pnl) >= max_risk:
                    msg = (
                        f"Handel gestoppt: Risiko pro Trade \u00fcberschritten ({limit}% )"
                    )
                    if hasattr(self.gui, "log_event"):
                        self.gui.log_event(f"🛑 {msg}")
                    print_warning(msg, warn_key="risk_pct")
                    print_stop_banner(msg)
                    self.gui.running = False
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

    def check_drawdown_pct_limit(self) -> bool:
        limit = self.drawdown_pct
        if limit is None:
            try:
                limit = float(self.gui.max_drawdown_pct.get())
            except Exception:
                return False
        if limit <= 0 or self.highest_capital <= 0:
            return False
        dd_pct = (
            (self.highest_capital - self.current_capital) / self.highest_capital * 100
        )
        if dd_pct >= limit:
            msg = f"Handel gestoppt: Drawdown {dd_pct:.2f}% \u00fcber Limit ({limit}%)"
            if hasattr(self.gui, "log_event"):
                self.gui.log_event(f"🛑 {msg}")
            print_warning(msg, warn_key="drawdown_pct")
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
            # CLEANUP: removed old debug print
            self.loss_count = 0

    # ------------------------------------------------------------------
    # New simplified risk logic

    def set_limits(self, max_risk: float, drawdown_limit: float) -> None:
        self.max_risk = max_risk
        self.drawdown_limit = drawdown_limit

    def set_start_capital(self, capital: float) -> None:
        self.initial_capital = capital

    def register_loss(self, loss_amount: float) -> bool:
        self.total_loss += loss_amount
        if self.get_drawdown_percent() >= self.drawdown_limit:
            logger.critical("❌ Drawdown-Limit erreicht – Bot wird deaktiviert.")
            return False
        return True

    def get_drawdown_percent(self) -> float:
        if self.initial_capital == 0:
            return 0.0
        return (self.total_loss / self.initial_capital) * 100

    def is_risk_too_high(self, expected_loss: float, balance: float) -> bool:
        max_allowed_loss = self.max_risk / 100 * balance
        return expected_loss > max_allowed_loss


