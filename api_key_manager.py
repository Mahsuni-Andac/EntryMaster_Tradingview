# api_key_manager.py
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class APICredentials:
    key: Optional[str] = None
    secret: Optional[str] = None

class APICredentialManager:

    def __init__(self) -> None:
        self._creds = APICredentials()

    def set_credentials(self, key: str, secret: str) -> None:
        self._creds.key = key.strip()
        self._creds.secret = secret.strip()

    def get_key(self) -> Optional[str]:
        return self._creds.key

    def get_secret(self) -> Optional[str]:
        return self._creds.secret

    def clear(self) -> None:
        self._creds = APICredentials()

    def load_from_env(self) -> bool:
        key = os.getenv("BITMEX_API_KEY")
        secret = os.getenv("BITMEX_API_SECRET")
        if key and secret:
            self.set_credentials(key, secret)
            return True
        return False
