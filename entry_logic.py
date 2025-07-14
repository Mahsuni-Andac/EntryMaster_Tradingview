# entry_logic.py
"""Simple wrapper around the entry indicator."""

from __future__ import annotations

from andac_entry_master import AndacEntryMaster, AndacSignal


def should_enter(candle: dict, indicator: AndacEntryMaster) -> AndacSignal:
    """Return the indicator evaluation for a given candle."""
    return indicator.evaluate(candle)
