"""Utility functions for dYdX v4 API connectivity."""

from typing import Tuple
import os
import requests
from config import SETTINGS

DEFAULT_DYDX_API_URL = "https://api.dydx.trade/v4"


def get_dydx_api_url() -> str:
    """Return configured base url for the dYdX v4 API."""
    return os.getenv("DYDX_API_URL") or SETTINGS.get("dydx_api_url", DEFAULT_DYDX_API_URL).rstrip("/")


def check_dydx_api() -> Tuple[bool, str]:
    """Check connectivity to the configured dYdX v4 endpoint."""
    url = f"{get_dydx_api_url()}/markets"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return True, "dYdX API erreichbar – Live-Marktdaten OK."
        return False, f"❌ dYdX API-Verbindung fehlgeschlagen: {resp.status_code} an {url}"
    except Exception as exc:  # pragma: no cover - network errors
        return False, f"❌ dYdX API-Ausnahme an {url}: {exc}"
