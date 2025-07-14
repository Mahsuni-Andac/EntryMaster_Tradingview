# simulator.py

from __future__ import annotations

import random
from dataclasses import dataclass

from pnl_utils import calculate_futures_pnl

@dataclass
class FeeModel:
    taker_fee: float = 0.00075
    slippage_range: tuple[float, float] = (-0.0003, 0.0003)
    funding_fee: float = 0.0  # placeholder, currently unused


def simulate_trade(entry_price: float, direction: str, exit_price: float,
                   amount: float, leverage: int, fee_model: FeeModel) -> tuple[float, float]:
    """Return executed exit price and pnl applying slippage and fees."""
    slip_exit = random.uniform(*fee_model.slippage_range)
    exec_exit = exit_price * (1 - slip_exit) if direction == "long" else exit_price * (1 + slip_exit)

    size = amount * leverage / entry_price
    fee = exec_exit * size * fee_model.taker_fee

    gross = calculate_futures_pnl(entry_price, exec_exit, leverage, amount, direction)
    pnl = gross - fee - fee_model.funding_fee

    return exec_exit, pnl
