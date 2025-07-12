"""Utility helpers for symbol name conversions."""

from __future__ import annotations


def bitmex_symbol(symbol: str) -> str:
    """Return BitMEX-compatible symbol for common USDT pairs.

    Converts standard "COINUSDT" names to BitMEX naming like "XBTUSD".
    If *symbol* is already BitMEX style or unknown, it is returned unchanged.
    """
    normalized = symbol.replace("/", "").replace("_", "").upper()
    mapping = {
        "BTCUSDT": "XBTUSD",
        "ETHUSDT": "ETHUSD",
    }
    return mapping.get(normalized, symbol)

