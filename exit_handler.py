# exit_handler.py

"""Logic to manage exits of active positions."""

from __future__ import annotations

import logging
from typing import Any, Dict


def handle_exit(
    position: Dict[str, Any],
    candle: Dict[str, Any],
    settings: Dict[str, Any],
    capital: float,
    app: Any,
    smart_cooldown: Any,
    now: float,
) -> Dict[str, Any]:
    """Check for SL/TP hits and close position if required."""
    if not position.get("active"):
        return position

    try:
        high = candle["high"]
        low = candle["low"]
        side = position["side"]
        sl = position["stop_loss"]
        tp = position["take_profit"]
        entry = position["entry_price"]
        size = position["size"]  # eingesetztes Kapital in USD
        leverage = position.get("leverage", 1)

        exited = False
        reason = ""
        exit_price = None

        if side == "LONG":
            if low <= sl:
                exit_price = sl
                reason = "STOP-LOSS"
                exited = True
            elif high >= tp:
                exit_price = tp
                reason = "TAKE-PROFIT"
                exited = True

        elif side == "SHORT":
            if high >= sl:
                exit_price = sl
                reason = "STOP-LOSS"
                exited = True
            elif low <= tp:
                exit_price = tp
                reason = "TAKE-PROFIT"
                exited = True

        if exited:
            direction = 1 if side == "LONG" else -1
            pnl = (
                (exit_price - entry) / entry
                * leverage
                * size
                * direction
            )
            position.update({
                "active": False,
                "exit_price": exit_price,
                "exit_time": now,
                "pnl": round(pnl, 2),
                "exit_reason": reason
            })

            logging.info(
                "🔁 EXIT (%s): %s @ %.2f | PnL: %.2f",
                reason,
                side,
                exit_price,
                pnl,
            )

            if smart_cooldown:
                smart_cooldown.register_sl(now)

        return position

    except Exception as exc:
        logging.error("❌ Fehler im Exit-Handler: %s", exc)
        return position
