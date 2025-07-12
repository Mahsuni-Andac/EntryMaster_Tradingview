from __future__ import annotations

"""Utility helpers for MEXC API connectivity."""

from typing import Tuple
import requests


def check_mexc_api(api_key: str | None, api_secret: str | None, symbol: str) -> Tuple[bool, str]:
    """Validate MEXC API credentials and availability of *symbol*.

    Returns ``(ok, message)`` with details on the result.
    """
    if not api_key and not api_secret:
        return False, "❌ API-Key und Secret fehlen"
    if not api_key:
        return False, "❌ API-Key fehlt"
    if not api_secret:
        return False, "❌ API-Secret fehlt"

    url = f"https://contract.mexc.com/api/v1/contract/detail?symbol={symbol}"
    try:
        resp = requests.get(url, timeout=10).json()
        if not resp.get("success"):
            return False, f"❌ API-Fehler: {resp.get('message', 'No message')}"
        if "data" not in resp:
            return False, "❌ Keine Daten in der API-Antwort"
        return True, "✅ Mexc API OK – Live-Marktdaten werden empfangen"
    except Exception as exc:
        return False, f"❌ Fehler beim API-Check: {exc}"

