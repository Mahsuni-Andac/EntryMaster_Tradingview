# pnl_utils.py

import logging


def calculate_futures_pnl(entry_price: float, exit_price: float, leverage: int, amount: float, side: str) -> float:
    direction = 1 if side == "long" else -1
    change = (exit_price - entry_price) / entry_price
    return change * leverage * amount * direction


def check_plausibility(pnl: float, old_balance: float, new_balance: float, amount: float) -> None:
    if abs(pnl) > 2 * amount or new_balance > 2 * old_balance or new_balance < 0:
        logging.warning(
            "Plausibilitätscheck: Ungewöhnlicher PnL oder Kontostand (%s -> %s, PnL %.2f)",
            old_balance,
            new_balance,
            pnl,
        )
