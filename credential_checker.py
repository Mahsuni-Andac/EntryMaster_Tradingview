import os
from typing import Tuple, Optional, Dict, List
import hashlib
import hmac
import time
from ecdsa import SigningKey, SECP256k1
from bech32 import bech32_encode, convertbits
from datetime import datetime

import requests
from dydx_api_utils import check_dydx_api

ENDPOINTS = {
    "mexc": "https://api.mexc.com/api/v3/ping",
    "binance": "https://api.binance.com/api/v3/ping",
    "bybit": "https://api.bybit.com/v2/public/time",
    "okx": "https://www.okx.com/api/v5/public/time",
    "bitmex": "https://www.bitmex.com/api/v1/instrument",
}

# Cache of last credential check results to avoid log spam
_last_statuses: Dict[str, Tuple[bool, str]] = {}
_last_active: List[str] = []
_last_live: Optional[bool] = None

def _timestamp() -> str:
    """Return current time string."""
    return datetime.now().strftime("[%H:%M:%S]")

def _detect_testnet(value: Optional[str]) -> bool:
    if not value:
        return False
    return "test" in value.lower()

def _derive_address(private_key: str, prefix: str = "dydx") -> str:
    """Return a cosmos bech32 address for *private_key*."""
    pk = private_key[2:] if private_key.startswith("0x") else private_key
    data = bytes.fromhex(pk)
    if len(data) != 32:
        raise ValueError("Kein gültiger Cosmos Private Key")
    sk = SigningKey.from_string(data, curve=SECP256k1)
    vk = sk.get_verifying_key()
    x = vk.pubkey.point.x()
    prefix_byte = b"\x02" if vk.pubkey.point.y() % 2 == 0 else b"\x03"
    compressed = prefix_byte + x.to_bytes(32, "big")
    rip = hashlib.new("ripemd160", hashlib.sha256(compressed).digest()).digest()
    five = convertbits(rip, 8, 5)
    if five is None:
        raise ValueError("Fehler bei Bech32-Konvertierung")
    return bech32_encode(prefix, five)

def check_exchange_credentials(
    exchange: str,
    key: Optional[str] = None,
    secret: Optional[str] = None,
    wallet: Optional[str] = None,
    private_key: Optional[str] = None,
) -> Tuple[bool, str]:
    """Validate credentials for a single exchange.

    Returns a tuple (ok, message).
    """
    ex = exchange.lower()
    try:
        if ex == "dydx":
            if not wallet or not private_key:
                return False, "❌ dYdX Wallet ungültig – Kein Zugriff"
            if not wallet.startswith("dydx1"):
                return False, "❌ Ungültige Wallet-Adresse"
            try:
                derived = _derive_address(private_key, "dydx")
            except Exception as exc:
                return False, f"❌ {exc}"
            if derived != wallet:
                return False, "❌ Adresse passt nicht zum Key"
            ok, api_msg = check_dydx_api()
            if not ok:
                return False, api_msg
            msg = "✅ dYdX Wallet gültig – Live-Marktdaten aktiv"
            if _detect_testnet(wallet):
                msg = "ℹ️ dYdX: Testnet Wallet erkannt, keine echten Trades möglich."
            return True, msg
        if ex in {"mexc", "binance", "bybit", "okx"}:
            if not key and not secret:
                return False, f"❌ {exchange} API ungültig: API-Key und Secret fehlen"
            if not key:
                return False, f"❌ {exchange} API ungültig: API-Key fehlt"
            if not secret:
                return False, f"❌ {exchange} API ungültig: API-Secret fehlt"
            if len(key) < 5 or len(secret) < 5:
                return False, f"❌ {exchange} API ungültig: Key/Secret zu kurz"
            endpoint = ENDPOINTS.get(ex)
            if endpoint:
                try:
                    requests.get(endpoint, timeout=5).raise_for_status()
                except Exception as exc:  # pragma: no cover - network issues
                    return False, f"❌ {exchange} Verbindung fehlgeschlagen: {exc}"
            msg = f"✅ {exchange} API OK – Live-Marktdaten werden empfangen"
            if _detect_testnet(key):
                msg = f"ℹ️ {exchange}: Testnet API erkannt, keine echten Trades möglich."
            return True, msg
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

def check_all_credentials(settings: Dict[str, str]) -> Dict[str, tuple]:
    """Check all supported exchanges and print status messages.

    Adds ``active`` and ``live`` keys to the result dict.
    """
    global _last_statuses, _last_active, _last_live

    results: Dict[str, tuple] = {}
    active: List[str] = []
    for exch in ["mexc", "dydx", "binance", "bybit", "okx", "bitmex"]:
        key = settings.get(f"{exch}_key") or os.getenv(f"{exch.upper()}_API_KEY")
        secret = settings.get(f"{exch}_secret") or os.getenv(f"{exch.upper()}_API_SECRET")
        wallet = None
        priv = None
        if exch == "dydx":
            wallet = settings.get("dydx_wallet") or os.getenv("DYDX_WALLET")
            priv = settings.get("dydx_private_key") or os.getenv("DYDX_PRIVATE_KEY")
        ok, msg = check_exchange_credentials(exch.capitalize(), key, secret, wallet, private_key=priv)
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
