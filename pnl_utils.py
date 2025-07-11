"""Utilities for PnL calculations in simulations."""

import logging


def calculate_futures_pnl(entry_price: float, exit_price: float, leverage: int, amount: float, side: str) -> float:
    """Calculate PnL for a futures trade using margin amount.

    Parameters
    ----------
    entry_price : float
        Price at entry.
    exit_price : float
        Price at exit.
    leverage : int
        Position leverage.
    amount : float
        Margin used for the trade in USD.
    side : str
        "long" or "short".

    Returns
    -------
    float
        Profit or loss in USD.
    """
    direction = 1 if side == "long" else -1
    change = (exit_price - entry_price) / entry_price
    return change * leverage * amount * direction


def check_plausibility(pnl: float, old_balance: float, new_balance: float, amount: float) -> None:
    """Log a warning if pnl or balance change seems implausible."""
    if abs(pnl) > 2 * amount or new_balance > 2 * old_balance or new_balance < 0:
        logging.warning(
            "Plausibilitätscheck: Ungewöhnlicher PnL oder Kontostand (%s -> %s, PnL %.2f)",
            old_balance,
            new_balance,
            pnl,
        )
