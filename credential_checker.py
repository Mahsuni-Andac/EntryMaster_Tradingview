import os
from typing import Tuple, Optional, Dict, List
import hashlib
import hmac
import time
from datetime import datetime

import requests
from config import SETTINGS

ENDPOINTS = {
    "bitmex": "https://www.bitmex.com/api/v1/instrument",
}

# Cache of last credential check results to avoid log spam
_last_statuses: Dict[str, Tuple[bool, str]] = {}
_last_active: List[str] = []
_last_live: Optional[bool] = None

def _timestamp() -> str:
    """Return current time string."""
    return datetime.now().strftime("[%H:%M:%S]")


def check_exchange_credentials(
    exchange: str,
    key: Optional[str] = None,
    secret: Optional[str] = None,
) -> Tuple[bool, str]:
    """Validate credentials for a single exchange.

    Returns a tuple (ok, message).
    """
    ex = exchange.lower()
    try:
        if ex == "bitmex":
            if not key and not secret:
                return False, "❌ BitMEX API ungültig: API-Key und Secret fehlen"
            if not key:
                return False, "❌ BitMEX API ungültig: API-Key fehlt"
            if not secret:
                return False, "❌ BitMEX API ungültig: API-Secret fehlt"
            if len(key) < 5 or len(secret) < 5:
                return False, "❌ BitMEX API ungültig: Key/Secret zu kurz"
            url = "https://www.bitmex.com/api/v1/user"
            expires = str(int(time.time()) + 5)
            message = "GET" + "/api/v1/user" + expires
            signature = hmac.new(
                secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            headers = {
                "api-key": key,
                "api-expires": expires,
                "api-signature": signature,
            }
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    return True, "✅ BitMEX API OK – Live-Marktdaten werden empfangen"
                if resp.status_code == 401:
                    return False, "❌ BitMEX API ungültig: Key oder Secret falsch oder Rechte fehlen."
                return False, f"❌ BitMEX API Fehler {resp.status_code}: {resp.text[:100]}"
            except Exception as exc:  # pragma: no cover - network
                return False, f"❌ BitMEX API-Ausnahme: {exc}"
        return False, "❌ Unbekannte Exchange"
    except Exception as e:  # pragma: no cover - safety
        return False, f"Fehler: {e}"

def check_all_credentials(settings: Dict[str, str], enabled: list[str] | None = None) -> Dict[str, tuple]:
    """Check credentials for the given exchanges.

    If *enabled* is ``None`` all known exchanges are checked. The result dict
    contains an ``active`` list and ``live`` flag.
    """
    global _last_statuses, _last_active, _last_live

    results: Dict[str, tuple] = {}
    active: List[str] = []
    exchanges = ["bitmex"]
    if enabled is not None:
        exchanges = [ex for ex in exchanges if ex in enabled]
    for exch in exchanges:
        key = settings.get(f"{exch}_key") or os.getenv(f"{exch.upper()}_API_KEY")
        secret = settings.get(f"{exch}_secret") or os.getenv(f"{exch.upper()}_API_SECRET")
        ok, msg = check_exchange_credentials(exch.capitalize(), key, secret)
        results[exch] = (ok, msg)

        if _last_statuses.get(exch) != (ok, msg):
            print(f"{_timestamp()} {msg}")
            _last_statuses[exch] = (ok, msg)
        if ok:
            active.append(exch)

    if active != _last_active:
        print(f"{_timestamp()} Aktive Exchanges: " + (", ".join(active) if active else "keine"))
        _last_active = active[:]

    live = any(ok for ok, _ in results.values())
    if _last_live is None or live != _last_live:
        print(f"{_timestamp()} Live-Marktdaten aktiv: " + ("✅" if live else "❌"))
        if not live:
            print(f"{_timestamp()} API nicht erreichbar – Bot pausiert")
        _last_live = live
    results["active"] = active
    results["live"] = live
    return results
