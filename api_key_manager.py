from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class APICredentials:
    """Speichert API-Zugangsdaten nur im Arbeitsspeicher."""
    key: Optional[str] = None
    secret: Optional[str] = None

class APICredentialManager:
    """Verwaltet API-Zugangsdaten sicher im RAM."""

    def __init__(self) -> None:
        self._creds = APICredentials()

    def set_credentials(self, key: str, secret: str) -> None:
        """Setzt API Key und Secret."""
        self._creds.key = key.strip()
        self._creds.secret = secret.strip()

    def get_key(self) -> Optional[str]:
        return self._creds.key

    def get_secret(self) -> Optional[str]:
        return self._creds.secret

    def clear(self) -> None:
        """Löscht die gespeicherten Zugangsdaten."""
        self._creds = APICredentials()

    def load_from_env(self) -> bool:
        """Lädt Zugangsdaten aus Umgebungsvariablen.

        Erwartet ``MEXC_API_KEY`` und ``MEXC_API_SECRET``. Gibt ``True`` zurück,
        wenn beide Werte gefunden wurden.
        """
        key = os.getenv("MEXC_API_KEY")
        secret = os.getenv("MEXC_API_SECRET")
        if key and secret:
            self.set_credentials(key, secret)
            return True
        return False
