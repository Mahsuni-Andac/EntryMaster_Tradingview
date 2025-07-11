# risk_manager.py
#
# Changelog:
# - Added drawdown limit support and highest capital tracking
# - Improved type hints and warnings
# - Unified warning messages with console_status helpers
# - Ignore zero/negative loss limit values

from __future__ import annotations

from typing import Optional

from console_status import print_warning, print_stop_banner


class RiskManager:
    """Simple risk management utility bound to a GUI instance."""

    def __init__(self, gui, start_capital: Optional[float] = None) -> None:
        self.gui = gui
        self.start_capital: float = start_capital or 0.0
        self.current_capital: float = start_capital or 0.0
        self.highest_capital: float = start_capital or 0.0
        self.running_loss: float = 0.0
        self.loss_count: int = 0

    def update_loss(self, realized_pnl: float) -> None:
        """Update current loss statistics after each trade."""
        self.running_loss += realized_pnl
        # Für consecutive Losses (optional, kann man ausbauen)
        if realized_pnl < 0:
            self.loss_count += 1
        else:
            self.loss_count = 0

    def update_capital(self, capital: float) -> None:
        """Update the stored current capital."""
        self.current_capital = capital
        self.highest_capital = max(self.highest_capital, capital)

    def check_loss_limit(self) -> bool:
        """Return ``True`` if the configured loss limit was exceeded."""
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
        """Return ``True`` if the configured drawdown limit was exceeded."""
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

    def reset_loss(self) -> None:
        """Reset stored loss statistics."""
        self.running_loss = 0.0
        self.loss_count = 0
        self.highest_capital = self.current_capital
        if hasattr(self.gui, "max_loss_status_label"):
            self.gui.max_loss_status_label.config(text="")
        if hasattr(self.gui, "max_drawdown_status_label"):
            self.gui.max_drawdown_status_label.config(text="")

    # Optional: Erweiterung für consecutive Losses, automatische längere Cooldowns usw.
    def handle_consecutive_loss(self, threshold: int = 3, cooldown_min: int = 30) -> None:
        """Placeholder for additional consecutive loss logic."""
        if self.loss_count >= threshold:
            print(f"🚨 {self.loss_count} Verluste in Folge! (Extra-Cooldown wäre hier möglich)")
            # Hier könnte man future logic für manuelles oder automatisches Cooldown ergänzen
            self.loss_count = 0

# Beispiel-Aufruf (kommt in deinen Hauptloop):
# if risk_manager.check_loss_limit():
#     time.sleep(1)
#     continue
# Nach jedem Trade:
# risk_manager.update_loss(pnl)

