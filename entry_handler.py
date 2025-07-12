# entry_handler.py

"""Utility to execute entries with a given trading backend."""

from __future__ import annotations

import logging
from typing import Any, Dict

from global_state import entry_time_global, atr_value_global, ema_trend_global

def handle_entry(
    signal: str,
    candle: Dict[str, Any],
    settings: Dict[str, Any],
    app: Any,
    capital: float,
    trader: Any,
    now: float,
    sl_mult: float,
    tp_mult: float,
    leverage: float,
) -> Dict[str, Any] | None:
    """Create a new trade based on *signal* and return the position state.

    Parameters
    ----------
    signal:
        Either ``"long"`` or ``"short"``.
    candle:
        Current market candle containing ``open``/``close``/``high``/``low``.
    settings:
        Runtime settings dictionary.
    app:
        GUI reference for callbacks (unused here but kept for compatibility).
    capital:
        Available capital for the trade.
    trader:
        Trading backend implementing ``place_order``.
    now:
        Timestamp of the current tick.
    sl_mult, tp_mult:
        Multipliers for ATR based SL/TP calculation.
    leverage:
        Account leverage.
    """
    try:
        direction = "long" if signal == "long" else "short"
        entry_price = float(candle["close"])
        atr = float(atr_value_global)
        capital = float(capital)

        # Positionsgröße entspricht dem eingesetzten Kapital (Margin)
        position_size = round(capital, 6)
        sl_distance = atr * sl_mult
        tp_distance = atr * tp_mult

        stop_loss = (
            round(entry_price - sl_distance, 2)
            if direction == "long"
            else round(entry_price + sl_distance, 2)
        )
        take_profit = (
            round(entry_price + tp_distance, 2)
            if direction == "long"
            else round(entry_price - tp_distance, 2)
        )

        # Order senden
        order = trader.place_order(
            side=direction,
            quantity=position_size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reduce_only=False
        )

        # Statusobjekt zurückgeben
        position = {
            "active": True,
            "symbol": settings.get("symbol", "BTCUSDT"),
            "side": direction.upper(),
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "size": position_size,
            "capital": capital,
            "leverage": leverage,
            "atr": atr,
            "ema_trend": ema_trend_global,
            "entry_time": entry_time_global,
            "api_response": order
        }

        logging.info(
            "✅ Entry ausgeführt: %s @ %.2f | SL: %.2f | TP: %.2f",
            direction.upper(),
            entry_price,
            stop_loss,
            take_profit,
        )
        return position

    except Exception as exc:
        logging.error("❌ Fehler beim Entry: %s", exc)
        return None
