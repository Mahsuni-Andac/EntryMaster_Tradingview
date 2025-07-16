# ADDED: centralized configuration management
"""Manage configuration from defaults, JSON, environment and GUI input."""

import json
import os
import logging
from typing import Any, Dict

# SETTINGS was previously defined in config.py which has been removed.
# Import defaults from the consolidated logic module instead.
from andac_entry_master import SETTINGS as DEFAULTS


class ConfigManager:
    """Combine configuration from multiple sources."""

    def __init__(self, defaults: Dict[str, Any] | None = None) -> None:
        self.values: Dict[str, Any] = dict(defaults or {})

    def load_json(self, path: str) -> None:
        """Load configuration from a JSON file."""
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.values.update(data)
        except Exception as exc:
            logging.getLogger(__name__).warning("Failed to load %s: %s", path, exc)

    def load_env(self, path: str = ".env") -> None:
        """Load simple KEY=VALUE pairs from an .env file."""
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip() or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, value = line.strip().split("=", 1)
                    os.environ.setdefault(key, value)
                    self.values[key] = value
        except Exception as exc:
            logging.getLogger(__name__).warning("Failed to load env %s: %s", path, exc)

    def override(self, params: Dict[str, Any]) -> None:
        """Override configuration with highest priority (e.g. GUI)."""
        self.values.update(params)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


# Singleton instance
config = ConfigManager(DEFAULTS.copy())
