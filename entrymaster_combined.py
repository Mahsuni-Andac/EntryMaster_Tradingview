# === from global_state.py ===
# global_state.py

from __future__ import annotations

from typing import Optional, Dict

entry_time_global: Optional[float] = None
ema_trend_global: str = "⬆️"
atr_value_global: float | None = None
position_global: Optional[Dict[str, float]] = None
last_feed_time: Optional[float] = None
last_candle_ts: Optional[int] = None

# Provide a simple module-like object for backward compatibility
class _GlobalStateProxy:
    def __getattr__(self, name):
        return globals().get(name)

    def __setattr__(self, name, value):
        globals()[name] = value

global_state = _GlobalStateProxy()

def reset_global_state() -> None:
    """Reset all global trading state variables."""
    global entry_time_global, ema_trend_global, atr_value_global, position_global, last_feed_time, last_candle_ts
    entry_time_global = None
    ema_trend_global = "⬆️"
    atr_value_global = 42.7
    position_global = None
    last_feed_time = None
    last_candle_ts = None


# === from status_events.py ===
# status_events.py
from typing import Callable, Dict, List, Optional

class StatusDispatcher:

    _subs: Dict[str, List[Callable[[bool, Optional[str]], None]]] = {
        "api": [],
        "feed": [],
    }

    @classmethod
    def subscribe(cls, event: str, func: Callable[[bool, Optional[str]], None]) -> None:
        cls._subs.setdefault(event, []).append(func)

    @classmethod
    def on_api_status(cls, func: Callable[[bool, Optional[str]], None]) -> None:
        cls.subscribe("api", func)

    @classmethod
    def on_feed_status(cls, func: Callable[[bool, Optional[str]], None]) -> None:
        cls.subscribe("feed", func)

    @classmethod
    def dispatch(cls, event: str, ok: bool, reason: Optional[str] = None) -> None:
        for cb in cls._subs.get(event, []):
            try:
                cb(ok, reason)
            except Exception:
                pass


# === from utils.py ===
import time
import logging


def retry_on_failure(retries: int = 3, delay: int = 2, backoff: int = 2):
    """Retry decorator for BitMEX orders."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    logging.warning(
                        "Retry %s/%s after error: %s", attempt + 1, retries, exc
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            logging.error(
                "Function %s failed after %s retries.", func.__name__, retries
            )
            return None

        return wrapper

    return decorator



# === from pnl_utils.py ===
# pnl_utils.py

import logging


def calculate_futures_pnl(entry_price: float, exit_price: float, leverage: int, amount: float, side: str) -> float:
    """Return the profit of a futures trade in USD."""
    direction = 1 if side == "long" else -1
    change = (exit_price - entry_price) / entry_price
    return change * leverage * amount * direction


def check_plausibility(pnl: float, old_balance: float, new_balance: float, amount: float) -> None:
    """Warn if PnL or balance jumps unrealistically."""
    if abs(pnl) > 2 * amount or new_balance > 2 * old_balance or new_balance < 0:
        logging.warning(
            "Plausibilitätscheck: Ungewöhnlicher PnL oder Kontostand (%s -> %s, PnL %.2f)",
            old_balance,
            new_balance,
            pnl,
        )


# === from simulator.py ===
# simulator.py

# from __future__ import annotations

import random
from dataclasses import dataclass

# from pnl_utils import calculate_futures_pnl

@dataclass
class FeeModel:
    taker_fee: float = 0.00075
    slippage_range: tuple[float, float] = (-0.0003, 0.0003)
    funding_fee: float = 0.0  # placeholder, currently unused


def simulate_trade(entry_price: float, direction: str, exit_price: float,
                   amount: float, leverage: int, fee_model: FeeModel) -> tuple[float, float]:
    """Return executed exit price and pnl applying slippage and fees."""
    slip_exit = random.uniform(*fee_model.slippage_range)
    exec_exit = exit_price * (1 - slip_exit) if direction == "long" else exit_price * (1 + slip_exit)

    size = amount * leverage / entry_price
    fee = exec_exit * size * fee_model.taker_fee

    gross = calculate_futures_pnl(entry_price, exec_exit, leverage, amount, direction)
    pnl = gross - fee - fee_model.funding_fee

    return exec_exit, pnl


# === from central_logger.py ===
# central_logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler
import time
from typing import List

class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = self.format(record)
            fallback = msg.encode("utf-8", "replace").decode("utf-8")
            stream = self.stream
            stream.write(fallback + self.terminator)
            self.flush()
        except ValueError:
            pass  # detached buffer Error fix

def setup_logging(level: int = logging.INFO, logfile: str = "bot.log") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            RotatingFileHandler(logfile, maxBytes=1_000_000, backupCount=3, encoding='utf-8'),
            SafeStreamHandler(sys.__stdout__)  # sicheres Original-stdout
        ],
    )

if not logging.getLogger().handlers:
    setup_logging()

_last_msg: str | None = None
_last_time: float = 0.0
_repeat: int = 0
_INTERVAL = 60.0

def log_messages(msg: str, level: int = logging.INFO) -> List[str]:
    global _last_msg, _last_time, _repeat
    now = time.time()
    out: List[str] = []
    if msg == _last_msg:
        if now - _last_time < _INTERVAL:
            _repeat += 1
            return out
        if _repeat:
            out.append(f"{msg} ({_repeat}x wiederholt)")
        else:
            out.append(msg)
        _last_time = now
        _repeat = 0
    else:
        if _last_msg is not None and _repeat:
            out.append(f"{_last_msg} ({_repeat}x wiederholt)")
        out.append(msg)
        _last_msg = msg
        _last_time = now
        _repeat = 0
    for line in out:
        logging.log(level, line)
    return out

def log_triangle_signal(signal_type: str, price: float) -> str:
    from datetime import datetime
    stamp = datetime.now().strftime("%H:%M:%S")
    if signal_type == "long":
        msg = f"{stamp} GRÜN Dreieck (LONG) erkannt @ {price:.2f}"
    elif signal_type == "short":
        msg = f"{stamp} ROT Dreieck (SHORT) erkannt @ {price:.2f}"
    else:
        msg = f"{stamp} Unbekanntes Signal"
    logging.info(msg)
    return msg


# === from bitmex_client.py ===
import os
import time
import hmac
import hashlib
import json
import logging
from typing import Optional

import requests


class BitmexClient:
    """Thin REST client for BitMEX Testnet."""

    def __init__(self,
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 base_url: str = "https://testnet.bitmex.com") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("BITMEX_API_KEY")
        self.api_secret = api_secret or os.getenv("BITMEX_API_SECRET")
        self.symbol = "XBTUSD"
        self.logger = logging.getLogger(__name__)

    # internal helper to create request headers
    def _headers(self, verb: str, endpoint: str, data: str = "") -> dict:
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not set")
        expires = str(int(time.time()) + 5)
        message = verb + endpoint + expires + data
        signature = hmac.new(
            self.api_secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        return {
            "api-expires": expires,
            "api-key": self.api_key,
            "api-signature": signature,
            "Content-Type": "application/json",
        }

    # basic request helper
    def _request(self, verb: str, endpoint: str, *, data: Optional[dict] = None) -> dict:
        body = json.dumps(data) if data else ""
        headers = self._headers(verb, endpoint, body)
        url = self.base_url + endpoint
        response = requests.request(verb, url, headers=headers, data=body, timeout=10)
        response.raise_for_status()
        return response.json()

    def place_order(
        self,
        side: str,
        quantity: float,
        reduce_only: bool = False,
        order_type: str = "Market",
    ) -> dict:
        side = side.upper()
        payload = {
            "symbol": self.symbol,
            "orderQty": quantity,
            "side": side,
            "ordType": order_type.capitalize(),
        }
        if reduce_only:
            payload["execInst"] = "ReduceOnly"
        return self._request("POST", "/api/v1/order", data=payload)

    def get_open_position(self) -> Optional[dict]:
        data = self._request("GET", "/api/v1/position")
        for pos in data:
            if pos.get("symbol") == self.symbol:
                return pos
        return None

    def close_position(self) -> Optional[dict]:
        pos = self.get_open_position()
        if not pos or not pos.get("currentQty"):
            return None
        side = "Sell" if pos["currentQty"] > 0 else "Buy"
        return self.place_order(side, abs(pos["currentQty"]), reduce_only=True)


# === from bitmex_interface.py ===
# bitmex_interface.py
"""Wrapper module exposing BitMEX REST calls via :class:`BitmexClient`."""

# from __future__ import annotations

import logging
from typing import Optional

# from bitmex_client import BitmexClient

logger = logging.getLogger(__name__)

# Instantiate a single client using credentials from environment variables
client = BitmexClient()


def bm_place_order(side: str, quantity: float, reduce_only: bool = False,
                   order_type: str = "Market") -> Optional[dict]:
    """Place an order on BitMEX."""
    try:
        return client.place_order(
            side, quantity, reduce_only=reduce_only, order_type=order_type
        )
    except Exception as exc:
        logger.error("❌ BitMEX-Order fehlgeschlagen: %s", exc)
        return None


def bm_close_position() -> Optional[dict]:
    """Close any open position using a market order."""
    try:
        return client.close_position()
    except Exception as exc:
        logger.error("close_position failed: %s", exc)
        return None


def bm_get_open_position() -> Optional[dict]:
    """Return current open position for XBTUSD if any."""
    try:
        return client.get_open_position()
    except Exception as exc:
        logger.error("get_open_position failed: %s", exc)
        return None


def set_credentials(key: str, secret: str) -> None:
    """Set API credentials for subsequent requests."""
    client.api_key = key
    client.api_secret = secret


def check_credentials() -> bool:
    """Verify that the current credentials are valid."""
    try:
        client.get_open_position()
        return True
    except Exception as exc:
        logger.error("check_credentials failed: %s", exc)
        return False



# === from config_manager.py ===
# ADDED: centralized configuration management
"""Manage configuration from defaults, JSON, environment and GUI input."""

import json
import os
import logging
from typing import Any, Dict

# SETTINGS was previously defined in config.py which has been removed.
# Import defaults from the consolidated logic module instead.
# from andac_entry_master import SETTINGS as DEFAULTS


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


# === from api_key_manager.py ===
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


# === from api_credential_frame.py ===
# api_credential_frame.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict

# from api_key_manager import APICredentialManager
# from status_events import StatusDispatcher
# Access bot settings from the consolidated module
# from andac_entry_master import SETTINGS
# from bitmex_interface import set_credentials, check_credentials

EXCHANGES = ["BitMEX"]

class APICredentialFrame(ttk.LabelFrame):

    def __init__(self, master: tk.Misc, cred_manager: APICredentialManager, log_callback=None) -> None:
        super().__init__(master, text="Exchange API")
        self.cred_manager = cred_manager
        self.log_callback = log_callback

        self.active_exchange = tk.StringVar(value=EXCHANGES[0])

        self.vars: Dict[str, Dict[str, tk.Variable]] = {}
        self.status_vars: Dict[str, tk.StringVar] = {}
        self.status_labels: Dict[str, ttk.Label] = {}

        self.data_source_mode = tk.StringVar(value="websocket")

        ttk.Label(self, text="Exchange:").grid(row=0, column=0, sticky="w")
        ttk.Label(self, text=EXCHANGES[0]).grid(row=0, column=1, sticky="w")

        start_row = 1
        for idx, exch in enumerate(EXCHANGES):
            row = start_row + idx
            status = tk.StringVar(value="⚪")
            self.status_vars[exch] = status
            key = tk.StringVar()
            secret = tk.StringVar()
            wallet = tk.StringVar()
            priv = tk.StringVar()
            self.vars[exch] = {
                "key": key,
                "secret": secret,
                "wallet": wallet,
                "priv": priv,
            }
            ttk.Label(self, text=f"API {exch}").grid(row=row, column=0, sticky="w")
            entry1 = ttk.Entry(self, textvariable=key, width=20, show="*")
            entry2 = ttk.Entry(self, textvariable=secret, width=20, show="*")
            entry1.grid(row=row, column=1, padx=2)
            entry2.grid(row=row, column=2, padx=2)
            lbl = ttk.Label(self, textvariable=status, foreground="grey")
            lbl.grid(row=row, column=3, padx=4)
            self.status_labels[exch] = lbl
            self.vars[exch]["entry1"] = entry1
            self.vars[exch]["entry2"] = entry2

        control_row = ttk.Frame(self)
        control_row.grid(row=start_row + len(EXCHANGES), column=0, columnspan=4, sticky="w", pady=5)
        ttk.Button(control_row, text="Speichern", command=self._save).pack(side="left")


        self.market_status = tk.StringVar(value="")

        status_row = ttk.Frame(self)
        status_row.grid(row=start_row + len(EXCHANGES) + 1, column=0, columnspan=4, sticky="w")

        self.market_status_label = ttk.Label(status_row, textvariable=self.market_status, foreground="red")
        self.market_status_label.pack(side="left")

        self.system_status = tk.StringVar(value="")
        self.system_status_label = ttk.Label(status_row, textvariable=self.system_status, foreground="green")
        self.system_status_label.pack(side="left", padx=(10, 0))

        self.feed_mode = tk.StringVar(value="")
        self.feed_mode_label = ttk.Label(status_row, textvariable=self.feed_mode, foreground="green")
        self.feed_mode_label.pack(side="left", padx=(10, 0))

        term_frame = tk.Frame(self, bg="black")
        term_frame.grid(row=0, column=4, rowspan=len(EXCHANGES)+1, padx=5, sticky="ne")
        self.price_terminal = tk.Text(term_frame, height=6, width=24, bg="black", fg="green", state="disabled")
        self.price_terminal.pack()

        self.check_market_feed()



    def log_price(self, text: str, error: bool = False) -> None:
        color = "red" if error else "green"
        self.price_terminal.config(state="normal", fg=color)
        self.price_terminal.insert("end", text + "\n")
        lines = self.price_terminal.get("1.0", "end-1c").splitlines()
        if len(lines) > 30:
            self.price_terminal.delete("1.0", f"{len(lines)-30 + 1}.0")
        self.price_terminal.see("end")
        self.price_terminal.config(state="disabled")

    def update_market_status(self, ok: bool) -> None:
        text = "✅ Marktdaten kommen an" if ok else "❌ Keine Marktdaten – bitte prüfen"
        color = "green" if ok else "red"
        self.market_status.set(text)
        self.market_status_label.config(foreground=color)

    def check_market_feed(self) -> None:
#         from data_provider import WebSocketStatus

        ok = WebSocketStatus.is_running()
        self.update_market_status(ok)

    def _save(self) -> None:
        exch = EXCHANGES[0]
        data = self.vars[exch]
        key = data["key"].get().strip()
        secret = data["secret"].get().strip()
        if not key or not secret:
            ok, msg = False, "API Key und Secret erforderlich"
        else:
            self.cred_manager.set_credentials(key, secret)
            set_credentials(key, secret)
            ok = check_credentials()
            msg = "API Daten gespeichert" if ok else "API Test fehlgeschlagen"
        if ok:
            SETTINGS[f"{exch.lower()}_key"] = key
            SETTINGS[f"{exch.lower()}_secret"] = secret
        else:
            self.cred_manager.clear()
            SETTINGS.pop(f"{exch.lower()}_key", None)
            SETTINGS.pop(f"{exch.lower()}_secret", None)
        SETTINGS["data_source_mode"] = "websocket"

        self.status_vars[exch].set("✅" if ok else "❌")
        self.status_labels[exch].config(foreground="green" if ok else "red")
        if self.log_callback:
            self.log_callback(msg)
        else:
            messagebox.showinfo("Status", msg)

        StatusDispatcher.dispatch("api", ok, None if ok else "Keine API aktiv")
        self.check_market_feed()


    def _test_api(self):
        print("🔍 Teste API-Zugriff (Platzhalter)")


# === from gui_model.py ===
# gui_model.py
"""Model holding GUI state variables and basic control helpers."""

# from __future__ import annotations

import tkinter as tk
from typing import Optional


class GUIModel:
    """Container for Tkinter variables and runtime state."""

    def __init__(self, root: tk.Misc) -> None:
        # runtime flags
        self.running: bool = False
        self.force_exit: bool = False
        self.should_stop: bool = False
        self.live_pnl: float = 0.0
        self.total_pnl: float = 0.0
        self.wins: int = 0
        self.losses: int = 0

        # general options
        self.auto_apply_recommendations = tk.BooleanVar(master=root, value=False)
        self.auto_multiplier = tk.BooleanVar(master=root, value=False)

        # Auto Partial Close
        self.apc_enabled = tk.BooleanVar(master=root, value=True)
        self.apc_rate = tk.StringVar(master=root, value="25")
        self.apc_interval = tk.StringVar(master=root, value="60")
        self.apc_min_profit = tk.StringVar(master=root, value="20")

        # risk limits
        self.max_loss_enabled = tk.BooleanVar(master=root, value=True)
        self.max_loss_value = tk.StringVar(master=root, value="60")
        self.risk_trade_pct = tk.StringVar(master=root, value="3.0")
        self.max_drawdown_pct = tk.StringVar(master=root, value="15.0")
        self.cooldown_minutes = tk.StringVar(master=root, value="2")

        # trading mode
        self.live_trading = tk.BooleanVar(master=root, value=False)
        self.paper_mode = tk.BooleanVar(master=root, value=True)
        self.trading_mode = tk.StringVar(master=root, value="paper")

        # basic parameters
        self.multiplier_var = tk.StringVar(master=root, value="10")
        self.capital_var = tk.StringVar(master=root, value="2000")

        # strategy options
        self.andac_lookback = tk.StringVar(master=root, value="20")
        self.andac_puffer = tk.StringVar(master=root, value="10.0")
        self.andac_vol_mult = tk.StringVar(master=root, value="1.2")

        self.andac_opt_rsi_ema = tk.BooleanVar(master=root)
        self.andac_opt_safe_mode = tk.BooleanVar(master=root)
        self.andac_opt_engulf = tk.BooleanVar(master=root)
        self.andac_opt_engulf_bruch = tk.BooleanVar(master=root)
        self.andac_opt_engulf_big = tk.BooleanVar(master=root)
        self.andac_opt_confirm_delay = tk.BooleanVar(master=root)
        self.andac_opt_mtf_confirm = tk.BooleanVar(master=root)
        self.andac_opt_volumen_strong = tk.BooleanVar(master=root)
        self.andac_opt_session_filter = tk.BooleanVar(master=root)

        self.use_doji_blocker = tk.BooleanVar(master=root)

        # timing
        self.interval = tk.StringVar(master=root, value="1m")
        self.use_time_filter = tk.BooleanVar(master=root)
        self.time_start = tk.StringVar(master=root, value="08:00")
        self.time_end = tk.StringVar(master=root, value="18:00")
        self.require_closed_candles = tk.BooleanVar(master=root, value=True)
        self.cooldown_after_exit = tk.StringVar(master=root, value="120")

        # manual SL/TP
        self.manual_sl_var = tk.StringVar(master=root, value="")
        self.manual_tp_var = tk.StringVar(master=root, value="")
        self.sl_tp_auto_active = tk.BooleanVar(master=root, value=False)
        self.sl_tp_manual_active = tk.BooleanVar(master=root, value=False)
        self.sl_tp_status_var = tk.StringVar(master=root, value="")
        self.last_reason_var = tk.StringVar(master=root, value="–")

        # expert settings
        self.entry_cooldown_seconds = tk.StringVar(master=root, value="60")
        self.sl_tp_mode = tk.StringVar(master=root, value="adaptive")
        self.min_profit_usd = tk.StringVar(master=root, value="1")
        self.partial_close_trigger = tk.StringVar(master=root, value="50")
        self.fee_model = tk.StringVar(master=root, value="0.075")
        self.max_trades_per_hour = tk.StringVar(master=root, value="5")

        # connection status
        self.feed_ok: bool = False
        self.api_ok: bool = False
        self.websocket_active: bool = False

    # --- helper methods -------------------------------------------------
    def toggle_manual_sl_tp(self, sl: Optional[str], tp: Optional[str]) -> bool:
        """Enable manual SL/TP if both values are valid."""
        try:
            float(sl.replace(",", "."))
            float(tp.replace(",", "."))
        except Exception:
            self.sl_tp_manual_active.set(False)
            return False

        self.manual_sl_var.set(sl)
        self.manual_tp_var.set(tp)
        self.sl_tp_manual_active.set(True)
        self.sl_tp_auto_active.set(False)
        return True

    def activate_auto_sl_tp(self) -> None:
        """Switch SL/TP handling to automatic mode."""
        self.sl_tp_auto_active.set(True)
        self.sl_tp_manual_active.set(False)

    def set_auto_sl_status(self, ok: bool) -> None:
        self.sl_tp_auto_active.set(ok)
        if ok:
            self.sl_tp_manual_active.set(False)

    def set_manual_sl_status(self, ok: bool) -> None:
        self.sl_tp_manual_active.set(ok)
        if ok:
            self.sl_tp_auto_active.set(False)


# === from gui_diagnose.py ===
import tkinter as tk
from tkinter import ttk
from datetime import datetime

# optionale kurze Erklärungen für wichtige Felder
DESCRIPTIONS = {
    "Multiplikator": "Gibt an, wie stark die Position gehebelt wird.",
    "Uhrzeit-Filter": "Nur innerhalb definierter Zeitfenster handeln",
    "Max Risiko pro Trade (%):": "Begrenzt das Risiko pro Trade.",
    "SL (%):": "Stop-Loss in Prozent",
    "TP (%):": "Take-Profit in Prozent",
}


def _widget_info(widget: tk.Widget) -> dict:
    name = ''
    if 'text' in widget.keys():
        name = widget.cget('text')
    if not name:
        name = getattr(widget, '_name', widget.winfo_class())
    value = ''
    try:
        if isinstance(widget, (tk.Entry, ttk.Entry)):
            value = widget.get()
            if value == '' and widget.cget('textvariable'):
                value = widget.getvar(widget.cget('textvariable'))
        elif isinstance(widget, tk.Text):
            value = widget.get('1.0', 'end').strip()
        elif isinstance(widget, ttk.Combobox):
            value = widget.get()
            if value == '' and widget.cget('textvariable'):
                value = widget.getvar(widget.cget('textvariable'))
        elif isinstance(widget, (tk.Checkbutton, ttk.Checkbutton, ttk.Radiobutton)):
            var = widget.cget('variable') or widget.cget('textvariable')
            if var:
                value = widget.getvar(var)
        elif 'text' in widget.keys():
            value = widget.cget('text')
    except Exception:
        value = ''
    visible = bool(widget.winfo_ismapped())
    has_logic = False
    try:
        if 'command' in widget.keys() and widget.cget('command'):
            has_logic = True
    except Exception:
        pass

    hints: list[str] = []
    if isinstance(widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)) and value == '':
        hints.append('kein Wert gesetzt')
    if isinstance(widget, (tk.Checkbutton, ttk.Checkbutton)) and not widget.cget('variable'):
        hints.append('keine Variable verbunden')
    if isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox)) and 'textvariable' in widget.keys() and not widget.cget('textvariable'):
        hints.append('keine Variable verbunden')

    desc = DESCRIPTIONS.get(name.rstrip(':'), '')

    return {
        'name': name,
        'type': widget.winfo_class(),
        'value': value,
        'visible': visible,
        'has_logic': has_logic,
        'hints': hints,
        'desc': desc,
    }


def generate_diagnose_md(root: tk.Widget, filename: str = 'gui_diagnose.md') -> None:
    report: list[str] = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report.append('# GUI Diagnose')
    report.append('')
    report.append('Automatisch erzeugter Bericht der Trading-GUI.')
    report.append(f'_Erstellt am {timestamp}_')
    report.append('')

    stats = {'total': 0, 'no_logic': 0, 'empty': 0}

    def walk(widget: tk.Widget, section: str | None = None):
        pending_label: str | None = None
        children = list(widget.winfo_children())
        idx = 0
        while idx < len(children):
            child = children[idx]
            if isinstance(child, ttk.Notebook):
                for tab_id in child.tabs():
                    frame = child.nametowidget(tab_id)
                    title = child.tab(tab_id, 'text') or frame.winfo_name()
                    report.append(f'## Abschnitt: {title}')
                    walk(frame, title)
            elif isinstance(child, (tk.LabelFrame, ttk.LabelFrame)):
                title = child.cget('text') or child.winfo_name()
                report.append(f'## Abschnitt: {title}')
                walk(child, title)
            elif isinstance(child, (tk.Frame, ttk.Frame)):
                walk(child, section)
            else:
                if isinstance(child, (tk.Label, ttk.Label)) and child.cget('text'):
                    pending_label = child.cget('text')
                    idx += 1
                    continue

                info = _widget_info(child)
                if pending_label:
                    info['name'] = pending_label
                    if not info['desc']:
                        info['desc'] = DESCRIPTIONS.get(pending_label.rstrip(':'), '')
                    pending_label = None
                stats['total'] += 1
                if not info['has_logic']:
                    stats['no_logic'] += 1
                if isinstance(child, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)) and info['value'] == '':
                    stats['empty'] += 1
                report.append(f"### Widget: {info['name']}")
                report.append(f"- Typ: {info['type']}")
                report.append(f"- Standardwert: {info['value']}")
                report.append(f"- Sichtbar: {'Ja' if info['visible'] else 'Nein'}")
                report.append(f"- Logik: {'Ja' if info['has_logic'] else 'Nein'}")
                if info['desc']:
                    report.append(f"- Funktion: {info['desc']}")
                if info['hints']:
                    report.append('- Hinweise:')
                    for h in info['hints']:
                        report.append(f'  - {h}')
                report.append('')

            idx += 1

    walk(root)

    report.append('---')
    report.append('## Zusammenfassung')
    report.append(f"- Anzahl aller Widgets: {stats['total']}")
    report.append(f"- Anzahl ohne Logik: {stats['no_logic']}")
    report.append(f"- Anzahl leerer Felder: {stats['empty']}")

    with open(filename, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(report))


def add_gui_diagnose_button(root: tk.Widget) -> None:
    btn = tk.Button(root, text='📋 GUI-Diagnose (Markdown)', command=lambda: generate_diagnose_md(root))
    btn.grid(row=999, column=0, columnspan=2, pady=10)



# === from neon_status_panel.py ===
# neon_status_panel.py
import tkinter as tk

NEON_COLORS = {
    "yellow": "#ffff33",
    "green": "#00ff00",
    "blue": "#00d0ff",
    "red": "#ff0033",
    "orange": "#ff9900",
}

class Tooltip:
    def __init__(self, widget, text=""):
        self.widget = widget
        self.text = text
        self.tipwindow = None

    def show(self, x, y):
        if self.tipwindow or not self.text:
            return
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{int(x)}+{int(y)}")
        label = tk.Label(tw, text=self.text, background="#222", foreground="white",
                         relief="solid", borderwidth=1, padx=4, pady=2)
        label.pack()

    def hide(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class NeonStatusPanel:

    BULB_SIZE = 20
    PADDING = 10

    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent)
        bg = parent.cget("bg") if isinstance(parent, tk.Widget) else None
        self.canvas = tk.Canvas(
            self.frame, width=30, bg=bg, highlightthickness=0
        )
        self.canvas.pack(fill="y", expand=False)

        self.items: dict[str, dict] = {}
        self.tooltip = Tooltip(self.canvas)
        self.max_rows = 0
        self.canvas.bind("<Configure>", lambda e: self._layout())
        self.frame.bind("<Configure>", lambda e: self._layout())

    def register(self, key: str, description: str):
        self.items[key] = {"item": None, "desc": description, "color": "yellow"}
        self._layout()

    def set_status(self, key: str, color: str, desc: str | None = None):
        if key not in self.items:
            return
        info = self.items[key]
        info["color"] = color
        if desc is not None:
            info["desc"] = desc
        if info["item"] is not None:
            self.canvas.itemconfigure(
                info["item"], fill=NEON_COLORS.get(color, color)
            )

    def _layout(self):
        if not self.items:
            return
        height = self.frame.winfo_height()
        if height <= 1:
            self.frame.after(50, self._layout)
            return

        max_rows = max(1, height // (self.BULB_SIZE + self.PADDING))
        if max_rows != self.max_rows:
            self.max_rows = max_rows

        cols = (len(self.items) + max_rows - 1) // max_rows
        self.canvas.config(width=30 * cols, height=height)
        self.canvas.delete("all")

        for index, (key, info) in enumerate(self.items.items()):
            col = index // max_rows
            row = index % max_rows
            x = 5 + col * 30
            y = 10 + row * (self.BULB_SIZE + self.PADDING)
            item = self.canvas.create_oval(
                x,
                y,
                x + self.BULB_SIZE,
                y + self.BULB_SIZE,
                fill=NEON_COLORS.get(info["color"], info["color"]),
                outline="",
            )
            info["item"] = item
            self.canvas.tag_bind(item, "<Enter>", lambda e, k=key: self._on_enter(e, k))
            self.canvas.tag_bind(item, "<Leave>", self._on_leave)

    def _on_enter(self, event, key):
        bbox = self.canvas.bbox(self.items[key]["item"])
        x = self.canvas.winfo_rootx() + bbox[2] + 5
        y = self.canvas.winfo_rooty() + bbox[1]
        self.tooltip.text = self.items[key]["desc"]
        self.tooltip.show(x, y)

    def _on_leave(self, event=None):
        self.tooltip.hide()


# === from trading_gui_logic.py ===
# trading_gui_logic.py

import json
import os
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import logging

TUNING_FILE = "tuning_config.json"

class TradingGUILogicMixin:
    def apply_recommendations(self):
        try:
            from datetime import datetime
#             from global_state import ema_trend_global, atr_value_global
            # SETTINGS moved to andac_entry_master
#             from andac_entry_master import SETTINGS

            volatility = atr_value_global
            if volatility is None:
                self.log_event("⚠️ ATR noch nicht verfügbar - Empfehlungen übersprungen")
                return
            # REMOVED: SessionFilter
            hour = datetime.utcnow().hour
            if 6 <= hour < 14:
                session = "london"
            elif 13 <= hour < 21:
                session = "new_york"
            else:
                session = "asia"
            performance = getattr(self, "live_pnl", 0.0)
            trend = ema_trend_global

            high_vol = volatility > 30
            spike = volatility > 80

            all_vars = [
                self.andac_opt_rsi_ema,
                self.andac_opt_safe_mode,
                self.andac_opt_engulf,
                self.andac_opt_engulf_bruch,
                self.andac_opt_engulf_big,
                self.andac_opt_confirm_delay,
                self.andac_opt_mtf_confirm,
                self.andac_opt_volumen_strong,
                self.andac_opt_session_filter,
                self.use_doji_blocker,
                self.use_time_filter,
            ]
            for var in all_vars:
                var.set(False)

            enable = []

            if spike:
                enable += [
                    self.andac_opt_safe_mode,
                    self.use_doji_blocker,
                    self.andac_opt_volumen_strong,
                ]
            elif high_vol:
                enable += [
                    self.andac_opt_engulf,
                    self.andac_opt_engulf_bruch,
                    self.andac_opt_volumen_strong,
                ]
            else:
                enable += [self.andac_opt_rsi_ema, self.andac_opt_safe_mode]

            if session in ("london", "new_york"):
                enable += [self.andac_opt_confirm_delay, self.andac_opt_mtf_confirm]
            else:
                enable.append(self.andac_opt_safe_mode)

            if performance < 0:
                enable += [self.andac_opt_safe_mode, self.use_doji_blocker]
            elif performance > 0:
                enable.append(self.andac_opt_engulf)

            if trend == "⬆️":
                enable.append(self.andac_opt_engulf_big)
            elif trend == "⬇️":
                enable.append(self.andac_opt_engulf_bruch)

            for var in set(enable):
                var.set(True)

            SETTINGS.update({
                "opt_rsi_ema": self.andac_opt_rsi_ema.get(),
                "opt_safe_mode": self.andac_opt_safe_mode.get(),
                "opt_engulf": self.andac_opt_engulf.get(),
                "opt_engulf_bruch": self.andac_opt_engulf_bruch.get(),
                "opt_engulf_big": self.andac_opt_engulf_big.get(),
                "opt_confirm_delay": self.andac_opt_confirm_delay.get(),
                "opt_mtf_confirm": self.andac_opt_mtf_confirm.get(),
                "opt_volumen_strong": self.andac_opt_volumen_strong.get(),
                "opt_session_filter": self.andac_opt_session_filter.get(),
            })

            self.log_event("✅ Auto-Empfehlungen angewendet")
        except Exception as e:
            self.log_event(f"⚠️ Fehler beim Anwenden: {e}")

    def disable_all_filters(self):
        try:
            for var in [
                self.andac_opt_rsi_ema,
                self.andac_opt_safe_mode,
                self.andac_opt_engulf,
                self.andac_opt_engulf_bruch,
                self.andac_opt_engulf_big,
                self.andac_opt_confirm_delay,
                self.andac_opt_mtf_confirm,
                self.andac_opt_volumen_strong,
                self.andac_opt_session_filter,
                self.use_time_filter,
                self.use_doji_blocker,
            ]:
                var.set(False)
            self.log_event("🧹 Alle Filter & Optionen deaktiviert")
        except Exception as e:
            self.log_event(f"⚠️ Fehler beim Deaktivieren: {e}")

    def update_auto_status(self):
        if self.auto_apply_recommendations.get():
            self.auto_status_label.config(text="🟢 Auto-Empfehlung aktiv")
        else:
            self.auto_status_label.config(text="")

    def start_bot(self):
        try:
            multiplier = float(self.multiplier_var.get().replace(",", "."))
            auto_multi = self.auto_multiplier.get()
            capital = float(self.capital_var.get().replace(",", "."))
        except ValueError as e:
            messagebox.showerror("Eingabefehler", f"Ungültige Zahl: {e}")
            return
        except Exception as e:
            self.log_event(f"⚠️ Fehler bei Eingaben: {e}")
            return
        if capital <= 0:
            self.log_event("⚠️ Einsatz muss größer 0 sein")
            return
        risk_pct = self._get_safe_float(self.risk_trade_pct, 3.0)
        drawdown_pct = self._get_safe_float(self.max_drawdown_pct, 15.0)
        cooldown = int(self.cooldown_minutes.get() or 2)

        try:
            entry_cooldown = int(self.entry_cooldown_seconds.get())
            cooldown_after_exit = int(self.cooldown_after_exit.get())
            sl_tp_mode = self.sl_tp_mode.get().lower()
            max_trades_hour = int(self.max_trades_per_hour.get())
            fee_percent = float(self.fee_model.get())
        except Exception:
            self.log_event("❗ Ungültige Expertenwerte – Standardwerte werden verwendet.")
            entry_cooldown = 60
            cooldown_after_exit = 120
            sl_tp_mode = "adaptive"
            max_trades_hour = 5
            fee_percent = 0.075

        if self.manual_sl_var.get() and self.manual_tp_var.get():
            sl_tp_mode = "manual"
            self.sl_tp_mode.set("manual")

        interval = self.interval.get()
        if hasattr(self, "bridge") and self.bridge is not None:
            self.bridge.update_params(
                multiplier,
                auto_multi,
                capital,
                interval,
                risk_pct,
                drawdown_pct,
                cooldown,
            )
        # SETTINGS has been relocated
#         from andac_entry_master import SETTINGS
        SETTINGS.update(
            {
                "risk_per_trade": risk_pct,
                "drawdown_pct": drawdown_pct,
                "cooldown": cooldown,
                "entry_cooldown": entry_cooldown,
                "cooldown_after_exit": cooldown_after_exit,
                "sl_tp_mode": sl_tp_mode,
                "max_trades_hour": max_trades_hour,
                "fee_percent": fee_percent,
                "opt_session_filter": self.andac_opt_session_filter.get(),
            }
        )

        filters = {
            "use_adaptive_sl": sl_tp_mode == "adaptive",
            "require_closed_candles": self.require_closed_candles.get(),
            "cooldown_after_exit": cooldown_after_exit,
            "sl_mode": sl_tp_mode,
            "opt_session_filter": self.andac_opt_session_filter.get(),
        }
        try:
            # Filter configuration helper is now bundled in andac_entry_master
#             from andac_entry_master import set_filter_config
            set_filter_config(filters)
        except Exception:
            pass
        if hasattr(self, "callback"):
            self.callback()

    def emergency_exit(self):
        try:
            if hasattr(self, "model"):
                self.model.running = False
            else:
                self.running = False
            if hasattr(self, "close_all_positions"):
                self.close_all_positions()
            self.log_event("❗️ Notausstieg ausgelöst! Alle Positionen werden geschlossen.")
        except Exception as e:
            print(f"❌ Fehler beim Notausstieg: {e}")

    def emergency_flat_position(self):
        if hasattr(self, "model"):
            self.model.force_exit = True
            self.model.running = False
        else:
            self.force_exit = True
            self.running = False
        self.log_event("⛔ Trade abbrechen: Die Position wird jetzt geschlossen.")
        
        if hasattr(self, 'position') and self.position is not None:
            self.position = cancel_trade(self.position, self)
            if self.position is None:
                logging.info("✅ Position wurde erfolgreich geschlossen und gel\u00f6scht.")
            else:
                logging.warning("\u26a0\ufe0f Position konnte nicht vollst\u00e4ndig entfernt werden.")
            self.log_event("✅ Position wurde erfolgreich geschlossen.")
        else:
            self.log_event("❌ Keine offene Position zum Abbrechen gefunden.")

    def abort_trade(self):
        if hasattr(self, "model"):
            self.model.force_exit = True
            self.model.running = False
        else:
            self.force_exit = True
            self.running = False

    def manual_yolo_entry(self):
#         from andac_entry_master import SETTINGS
#         from data_provider import get_live_candles, fetch_last_price
#         from realtime_runner import simulate_trade
        from tkinter import messagebox
        import time

        candles = get_live_candles(10)
        if len(candles) < 10:
            messagebox.showwarning("Nicht genug Daten", "Mindestens 10 Candles nötig.")
            return

        last_10 = candles[-10:]
        avg_open = sum(c["open"] for c in last_10) / 10
        avg_close = sum(c["close"] for c in last_10) / 10
        direction = "long" if avg_close > avg_open else "short"

        price = fetch_last_price()
        if price is None:
            messagebox.showerror("Keine Daten", "Preis konnte nicht ermittelt werden.")
            return

        capital = SETTINGS.get("capital", 1000)
        leverage = SETTINGS.get("leverage", 20)
        amount = capital * leverage / price

        sl = price * (0.995 if direction == "long" else 1.005)
        tp = price * (1.01 if direction == "long" else 0.99)

        position = {
            "entry": price,
            "amount": amount,
            "side": direction,
            "tp": tp,
            "sl": sl,
            "leverage": leverage,
            "entry_index": 0,
        }

        logging.info(
            f"[{time.strftime('%H:%M:%S')}] \U0001F680 Trend-Entry (10C): {direction.upper()} @ {price:.2f}"
        )

        if SETTINGS.get("paper_mode", True):
            current_index = 0
            SETTINGS["capital"] = simulate_trade(position, price, current_index, SETTINGS, capital)
            self.update_capital(SETTINGS["capital"])
        else:
#             from andac_entry_master import open_position
            res = open_position("BUY" if direction == "long" else "SELL", amount)
            if not res:
                messagebox.showerror("Fehlgeschlagen", "Live-Order konnte nicht gesendet werden.")

    def update_live_trade_pnl(self, pnl):
        color = "green" if pnl >= 0 else "red"
        self.pnl_value.config(text=f"📉 PnL: {pnl:.2f} $", foreground=color)

    def update_last_trade(self, side: str, entry: float, exit_price: float, pnl: float):
        text = f"{side.upper()} {entry:.2f}->{exit_price:.2f} ({pnl:.2f}$)"
        if hasattr(self, "last_trade_label"):
            self.last_trade_label.config(text=text)

    def update_stats(self, pnl: float):
        if hasattr(self, "model"):
            self.model.total_pnl += pnl
            if pnl >= 0:
                self.model.wins += 1
            else:
                self.model.losses += 1
            if hasattr(self, "total_pnl_label"):
                self.total_pnl_label.config(text=f"Gesamt PnL: {self.model.total_pnl:.2f} $")
            if hasattr(self, "trade_count_label"):
                self.trade_count_label.config(text=f"Trades {self.model.wins}/{self.model.losses}")

    def update_capital(self, capital):
        self.capital_value.config(text=f"💰 Kapital: ${capital:.2f}")

    def update_api_status(self, ok: bool, reason: str | None = None) -> None:
        if getattr(self, "_last_api_status", (None, None)) == (ok, reason):
            return
        self._last_api_status = (ok, reason)
        if hasattr(self, "model"):
            self.model.api_ok = ok
        else:
            self.api_ok = ok
        stamp = datetime.now().strftime("%H:%M:%S")
        if ok:
            text = "BitMEX API ✅"
            color = "green"
        else:
            text = f"BitMEX API ❌" + (f" – {reason} ({stamp})" if reason else f" ({stamp})")
            color = "red"
        if hasattr(self, "api_status_var"):
            self.api_status_var.set(text)
        if hasattr(self, "api_status_label"):
            self.api_status_label.config(foreground=color)
            if not self.api_status_label.winfo_ismapped():
                self.api_status_label.pack(side="left", padx=10)
        if hasattr(self, "neon_panel"):
            self.neon_panel.set_status("api", color, text)

    def update_feed_status(self, ok: bool, reason: str | None = None) -> None:
        if getattr(self, "_last_feed_status", (None, None)) == (ok, reason):
            return
        self._last_feed_status = (ok, reason)
        if hasattr(self, "model"):
            self.model.feed_ok = ok
        else:
            self.feed_ok = ok
        if reason == "REST-API-Call-14":
            color = "orange"
            text = reason
            if hasattr(self, "feed_mode_var"):
                self.feed_mode_var.set(reason)
        else:
            self._update_feed_mode_display(ok)
            color = "green" if ok else "red"
            text = "✅ Feed stabil" if ok else "❌ Kein Feed"
            if not ok and reason:
                if "Reconnect" in reason:
                    color = "orange"
                    text = f"🔄 {reason}"
                else:
                    text = f"❌ {reason}"

        if hasattr(self, "feed_status_var"):
            self.feed_status_var.set(text if not ok else "")
        if hasattr(self, "feed_status_label"):
            self.feed_status_label.config(foreground=color)
            if not ok and not self.feed_status_label.winfo_ismapped():
                self.feed_status_label.pack(side="left", padx=10)
            elif ok and self.feed_status_label.winfo_ismapped():
                self.feed_status_label.pack_forget()
        if hasattr(self, "neon_panel"):
            self.neon_panel.set_status("feed", color, text)
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "update_market_status"):
            self.api_frame.update_market_status(ok)

    def _update_feed_mode_display(self, ok: bool) -> None:
        if not ok:
            text = "Binance WebSocket ❌"
            color = "red"
        else:
            text = "Binance WebSocket OK"
            color = "green"

        if hasattr(self, "feed_mode_var"):
            self.feed_mode_var.set(text)
        if hasattr(self, "feed_mode_label"):
            self.feed_mode_label.config(foreground=color)
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "feed_mode_label"):
            self.api_frame.feed_mode_label.config(foreground=color)

    def update_exchange_status(self, exchange: str, ok: bool) -> None:
        if hasattr(self, "exchange_status_vars") and exchange in self.exchange_status_vars:
            cache = getattr(self, "exchange_status_cache", None)
            if cache is not None:
                cache[exchange] = ok
            if getattr(self, "_last_exchange_status", {}).get(exchange) == ok:
                return
            self._last_exchange_status = getattr(self, "_last_exchange_status", {})
            self._last_exchange_status[exchange] = ok
            lbl = self.exchange_status_labels.get(exchange)
            if ok:
                if lbl and lbl.winfo_ismapped():
                    lbl.pack_forget()
                self.exchange_status_vars[exchange].set("")
            else:
                stamp = datetime.now().strftime("%H:%M:%S")
                text = f"{exchange} ❌ ({stamp})"
                self.exchange_status_vars[exchange].set(text)
                if lbl:
                    lbl.config(foreground="red")
                    if not lbl.winfo_ismapped():
                        lbl.pack(side="left", padx=5)


    def update_pnl(self, pnl):
        self.update_stats(pnl)
        self.log_event(f"💰 Trade abgeschlossen: PnL {pnl:.2f} $")

    def log_event(self, msg):
#         from central_logger import log_messages

        ignore = ["Antwort unvollständig"]
        if any(txt in msg for txt in ignore):
            return

        for line in log_messages(msg):
            self.log_box.insert("end", f"{line}\n")
        lines = self.log_box.get("1.0", "end-1c").splitlines()
        if len(lines) > 30:
            self.log_box.delete("1.0", f"{len(lines)-30 + 1}.0")
        self.log_box.see("end")

    def _log_error_once(self, text: str) -> None:
        if not hasattr(self, "_error_cache"):
            self._error_cache = set()
        if text in self._error_cache:
            return
        self._error_cache.add(text)
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_event(f"[{stamp}] ❌ Wirksamkeit: {text}")

    def save_to_file(self, filename=TUNING_FILE):
        state = {}
        for k, v in vars(self).items():
            if isinstance(v, tk.Variable):
                state[k] = v.get()
            elif isinstance(v, (str, float, int, bool)):
                state[k] = v
        if hasattr(self, "time_filters"):
            state["time_filters"] = [
                (start.get(), end.get()) for (start, end) in self.time_filters
            ]
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            self.log_event("💾 Einstellungen gespeichert")
            if hasattr(self, "neon_panel"):
                self.neon_panel.set_status("saved", "green", "Konfiguration gespeichert")
        except Exception as e:
            self.log_event(f"Fehler beim Speichern: {e}")

    def load_from_file(self, filename=TUNING_FILE):
        if not os.path.exists(filename):
            self.log_event(f"Keine Konfigurationsdatei {filename} gefunden")
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                state = json.load(f)
            for k, v in state.items():
                if hasattr(self, k):
                    var = getattr(self, k)
                    if isinstance(var, tk.Variable):
                        var.set(v)
            if "time_filters" in state and hasattr(self, "time_filters"):
                loaded_filters = state["time_filters"]
                if len(loaded_filters) == len(self.time_filters):
                    for (start_val, end_val), (start, end) in zip(loaded_filters, self.time_filters):
                        start.set(start_val)
                        end.set(end_val)
            self.log_event("⏏️ Einstellungen geladen")
        except Exception as e:
            self.log_event(f"Fehler beim Laden: {e}")

    def _collect_settings(self):
        return {
            k: (
                self._convert_strvar(v) if isinstance(v, tk.StringVar)
                else v.get()
            )
            for k, v in self.__dict__.items()
            if isinstance(v, (tk.StringVar, tk.BooleanVar))
        }

    def _convert_strvar(self, var):
        try:
            val = var.get()
            if val.replace(".", "", 1).isdigit():
                return float(val) if "." in val else int(val)
            return val
        except:
            return var.get()

    def _get_safe_float(self, var, default=None):
        try:
            return float(var.get().replace(",", "."))
        except (ValueError, AttributeError):
            return default

    def toggle_manual_sl_tp(self):
        current = self.sl_tp_manual_active.get()
        self.sl_tp_manual_active.set(not current)
        self.update_manual_sl_tp_status()
        state = "aktiviert" if self.sl_tp_manual_active.get() else "deaktiviert"
        self.log_event(f"📝 Manuelles SL/TP {state}")

    def update_manual_sl_tp_status(self):
#         from andac_entry_master import SETTINGS

        if self.sl_tp_manual_active.get():
            if hasattr(self, "toggle_sl_tp_button"):
                self.toggle_sl_tp_button.config(text="SL/TP EIN")
            msg = "✅ SL/TP Aktiv"
            color = "green"
            SETTINGS["sl_tp_manual_active"] = True
        else:
            if hasattr(self, "toggle_sl_tp_button"):
                self.toggle_sl_tp_button.config(text="SL/TP AUS")
            msg = "❌ Aus: Gegensignal ist dein einziger Exit ⚠️"
            color = "red"
            SETTINGS["sl_tp_manual_active"] = False

        if hasattr(self, "sl_tp_hint_label"):
            self.sl_tp_hint_label.config(text=msg, foreground=color)
        if hasattr(self, "sl_tp_status_var"):
            self.sl_tp_status_var.set(msg)

    def save_manual_sl(self):
#         from andac_entry_master import SETTINGS

        try:
            sl = float(self.manual_sl_var.get())
            if sl <= 0:
                raise ValueError
            SETTINGS["manual_sl"] = sl
            messagebox.showinfo("SL gespeichert", f"Stop Loss: {sl:.2f} % gesetzt.")
        except Exception:
            messagebox.showerror(
                "Ungültiger SL",
                "Bitte gültigen SL in Prozent eingeben (z. B. 0.5)",
            )

    def save_manual_tp(self):
#         from andac_entry_master import SETTINGS

        try:
            tp = float(self.manual_tp_var.get())
            if tp <= 0:
                raise ValueError
            SETTINGS["manual_tp"] = tp
            messagebox.showinfo("TP gespeichert", f"Take Profit: {tp:.2f} % gesetzt.")
        except Exception:
            messagebox.showerror(
                "Ungültiger TP",
                "Bitte gültigen TP in Prozent eingeben (z. B. 1.0)",
            )

    def activate_auto_sl_tp(self):
        if hasattr(self, "model"):
            self.model.activate_auto_sl_tp()
        else:
            self.sl_tp_auto_active.set(True)
            self.sl_tp_manual_active.set(False)
        self.log_event("⚙️ Adaptive SL/TP aktiviert")

    def set_auto_sl_status(self, ok: bool) -> None:
        if hasattr(self, "model"):
            self.model.set_auto_sl_status(ok)
        else:
            self.sl_tp_auto_active.set(ok)
            if ok:
                self.sl_tp_manual_active.set(False)

    def set_manual_sl_status(self, ok: bool) -> None:
        if hasattr(self, "model"):
            self.model.set_manual_sl_status(ok)
        else:
            self.sl_tp_manual_active.set(ok)
            if ok:
                self.sl_tp_auto_active.set(False)

def stop_and_reset(self):
    if hasattr(self, "model"):
        self.model.should_stop = True
        self.model.running = False
    else:
        self.should_stop = True
        self.running = False
    try:
        self.log_event("🧹 Bot gestoppt – Keine Rücksetzung der Konfiguration vorgenommen.")
    except Exception as e:
        self.log_event(f"❌ Fehler beim Anhalten des Bots: {e}")



# === from trading_gui_core.py ===
# trading_gui_core.py

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import logging

# from trading_gui_logic import TradingGUILogicMixin
# from gui_model import GUIModel
# from api_credential_frame import APICredentialFrame, EXCHANGES
# from neon_status_panel import NeonStatusPanel
# from api_key_manager import APICredentialManager
# from status_events import StatusDispatcher
# from gui_diagnose import add_gui_diagnose_button

class TradingGUI(TradingGUILogicMixin):
    def __getattr__(self, item):
        model = self.__dict__.get("model")
        if model and hasattr(model, item):
            return getattr(model, item)
        raise AttributeError(item)

    def __setattr__(self, key, value):
        model = self.__dict__.get("model")
        if key != "model" and model and hasattr(model, key):
            setattr(model, key, value)
        else:
            super().__setattr__(key, value)
    def __init__(self, root, cred_manager: APICredentialManager | None = None):
        self.root = root
        self.root.title("🧞‍♂️ EntryMaster_Tradingview – Kapital-Safe Edition")

        self.cred_manager = cred_manager or APICredentialManager()

        # hold all Tk variables and runtime flags
        self.model = GUIModel(root)
        self.apc_status_label = None
        self.max_loss_status_label = None


        self.multiplier_entry = None
        self.capital_entry = None
        self.log_box = None
        self.auto_status_label = None

        # trade history and open position tracking
        self.trade_history = []
        self.current_position = None
        self.trade_box = None

        # references to model variables for convenience
        self.live_trading = self.model.live_trading
        self.paper_mode = self.model.paper_mode
        self.trading_mode = self.model.trading_mode
        self.mode_label = None

        self.style = ttk.Style()
        self.style.configure("AutoSL.TButton", foreground="black")
        self.style.configure("ManualSL.TButton", foreground="black")

        self._init_variables()
        self._build_gui()
        self._init_neon_panel()
        self._collect_setting_vars()
        self._build_status_panel()
        StatusDispatcher.on_api_status(self.update_api_status)
        StatusDispatcher.on_feed_status(self.update_feed_status)


        # SETTINGS now resides in andac_entry_master
#         from andac_entry_master import SETTINGS
        SETTINGS["data_source_mode"] = "websocket"
        self.model.websocket_active = True
        self._update_feed_mode_display(False)

        self.market_interval_ms = 1000
        self._update_market_monitor()

        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = int(self.root.winfo_height() * 0.9) - 30
        if height < 200:
            height = int(self.root.winfo_height() * 0.9)
        self.root.geometry(f"{width}x{height}")

        self.update_trade_display()

    def _init_neon_panel(self):
        self.neon_panel = NeonStatusPanel(self.root)
        self.neon_panel.frame.pack(side="right", fill="y", padx=(0, 5))

        mapping = {
            "api": ("API Status", None),
            "feed": ("Datenfeed", None),
            "apc": ("Auto Partial Close", self.apc_enabled),
            "loss": ("Verlustlimit", self.max_loss_enabled),
            "auto_rec": ("Auto Empfehlungen", self.auto_apply_recommendations),
            "auto_multi": ("Auto Multiplikator", self.auto_multiplier),
            "safe": ("Sicherheitsfilter", self.andac_opt_safe_mode),
            "vol": ("Volumenfilter", self.andac_opt_volumen_strong),
            "paper": ("Paper-Trading aktiv", self.paper_mode),
            "saved": ("Konfiguration gespeichert", None),
        }

        self._neon_vars = {}
        for key, (desc, var) in mapping.items():
            self.neon_panel.register(key, desc)
            if isinstance(var, tk.BooleanVar):
                self._neon_vars[key] = var
                var.trace_add("write", lambda *a, k=key, v=var: self._update_neon_var(k, v))
                self._update_neon_var(key, var)
        self.neon_panel.set_status("saved", "blue", "Noch nicht gespeichert")

    def _update_neon_var(self, key, var):
        color = "green" if var.get() else "blue"
        self.neon_panel.set_status(key, color)

    def _update_mode_label(self):
        if self.live_trading.get():
            text = "Live Trading"
            color = "red"
        else:
            text = "Paper Trading"
            color = "blue"
        if self.mode_label is not None:
            self.mode_label.config(text=text, foreground=color)

    def _on_mode_toggle(self):
        self.live_trading.set(self.trading_mode.get() == "live")
        self.paper_mode.set(not self.live_trading.get())
        self._update_mode_label()

    def _init_variables(self):
        # use variables from the model
        self.multiplier_var = self.model.multiplier_var
        self.capital_var = self.model.capital_var

        self.andac_lookback = self.model.andac_lookback
        self.andac_puffer = self.model.andac_puffer
        self.andac_vol_mult = self.model.andac_vol_mult

        self.andac_opt_rsi_ema = self.model.andac_opt_rsi_ema
        self.andac_opt_safe_mode = self.model.andac_opt_safe_mode
        self.andac_opt_engulf = self.model.andac_opt_engulf
        self.andac_opt_engulf_bruch = self.model.andac_opt_engulf_bruch
        self.andac_opt_engulf_big = self.model.andac_opt_engulf_big
        self.andac_opt_confirm_delay = self.model.andac_opt_confirm_delay
        self.andac_opt_mtf_confirm = self.model.andac_opt_mtf_confirm
        self.andac_opt_volumen_strong = self.model.andac_opt_volumen_strong

        self.andac_opt_session_filter = self.model.andac_opt_session_filter

        self.use_doji_blocker = self.model.use_doji_blocker

        self.interval = self.model.interval
        self.use_time_filter = self.model.use_time_filter
        self.time_start = self.model.time_start
        self.time_end = self.model.time_end
        self.require_closed_candles = self.model.require_closed_candles
        self.cooldown_after_exit = self.model.cooldown_after_exit

        self.rsi_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.volume_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.volboost_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.ema_rec_label = ttk.Label(self.root, text="", foreground="green")
        
        self.bigcandle_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.breakout_rec_label = ttk.Label(self.root, text="", foreground="green")
        self.rsi_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.volume_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.volboost_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.ema_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.doji_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.engulfing_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.bigcandle_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.breakout_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.safemode_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.engulf_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.cool_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.safe_chk_rec = ttk.Label(self.root, text="", foreground="green")
        self.auto_status_label = None

        self.manual_sl_var = self.model.manual_sl_var
        self.manual_tp_var = self.model.manual_tp_var
        self.sl_tp_auto_active = self.model.sl_tp_auto_active
        self.sl_tp_manual_active = self.model.sl_tp_manual_active
        self.sl_tp_status_var = self.model.sl_tp_status_var
        self.last_reason_var = self.model.last_reason_var

        # expert settings
        self.entry_cooldown_seconds = self.model.entry_cooldown_seconds
        self.sl_tp_mode = self.model.sl_tp_mode
        self.min_profit_usd = self.model.min_profit_usd
        self.partial_close_trigger = self.model.partial_close_trigger
        self.fee_model = self.model.fee_model
        self.max_trades_per_hour = self.model.max_trades_per_hour

        self.risk_trade_pct = self.model.risk_trade_pct
        self.max_drawdown_pct = self.model.max_drawdown_pct
        self.cooldown_minutes = self.model.cooldown_minutes

        self.api_status_var = tk.StringVar(value="BitMEX API ❌")
        self.feed_status_var = tk.StringVar(value="Feed ❌")
        self.api_status_label = None
        self.feed_status_label = None
        self.feed_ok = self.model.feed_ok
        self.api_ok = self.model.api_ok
        self.websocket_active = self.model.websocket_active

        self.exchange_status_vars = {ex: tk.StringVar(value="⚪") for ex in EXCHANGES}
        self.exchange_status_labels = {}
        self.exchange_status_cache = {}

    def _build_gui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side="left", fill="both", expand=True)

        top_info = ttk.Frame(self.main_frame)
        top_info.pack(pady=5)
        self._build_api_credentials(top_info)
        self.capital_value = ttk.Label(top_info, text="💰 Kapital: $0", foreground="green", font=("Arial", 11, "bold"))
        self.capital_value.pack(side="left", padx=10)
        self.pnl_value = ttk.Label(top_info, text="📉 PnL: $0", foreground="black", font=("Arial", 11, "bold"))
        self.pnl_value.pack(side="left", padx=10)
        self.total_pnl_label = ttk.Label(top_info, text="Gesamt PnL: $0", foreground="black", font=("Arial", 11, "bold"))
        self.total_pnl_label.pack(side="left", padx=10)
        self.last_trade_label = ttk.Label(top_info, text="Letzter Trade: ---", foreground="blue", font=("Arial", 10))
        self.last_trade_label.pack(side="left", padx=10)
        self.trade_count_label = ttk.Label(top_info, text="Trades 0/0", foreground="blue", font=("Arial", 10))
        self.trade_count_label.pack(side="left", padx=10)

        self.api_status_label = ttk.Label(top_info, textvariable=self.api_status_var, foreground="red", font=("Arial", 11, "bold"))
        self.api_status_label.pack(side="left", padx=10)
        self.feed_status_label = ttk.Label(top_info, textvariable=self.feed_status_var, foreground="red", font=("Arial", 11, "bold"))
        self.feed_status_label.pack(side="left", padx=10)
        self.mode_label = ttk.Label(top_info, text="Paper Trading", foreground="blue", font=("Arial", 11, "bold"))
        self.mode_label.pack(side="left", padx=10)

        mode_frame = ttk.Frame(top_info)
        mode_frame.pack(side="left")
        ttk.Radiobutton(
            mode_frame,
            text="Paper Trading",
            variable=self.trading_mode,
            value="paper",
            command=self._on_mode_toggle,
        ).pack(side="left")
        ttk.Radiobutton(
            mode_frame,
            text="Live Trading",
            variable=self.trading_mode,
            value="live",
            command=self._on_mode_toggle,
        ).pack(side="left")
        self._on_mode_toggle()

#         from data_provider import init_price_var, price_var
        init_price_var(self.root)
        self.yolo_button = ttk.Button(top_info, text="🚀 10C Entry", command=self.manual_yolo_entry)
        self.yolo_button.pack(side="right", padx=5)
        self.price_label = ttk.Label(top_info, textvariable=price_var, foreground="blue", font=("Arial", 11, "bold"))
        self.price_label.pack(side="right", padx=10)

        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(padx=10, pady=5, fill="both", expand=True)

        container = ttk.Frame(notebook)
        expert_container = ttk.Frame(notebook)
        notebook.add(container, text="Einstellungen")
        notebook.add(expert_container, text="Experteneinstellungen")
        risk = ttk.Frame(container)
        left = ttk.Frame(container)
        right = ttk.Frame(container)
        middle = ttk.Frame(container)
        extra = ttk.Frame(container)
        andac = ttk.Frame(container)

        risk.grid(row=0, column=0, padx=10, sticky="nw")
        left.grid(row=0, column=1, padx=10, sticky="ne")
        right.grid(row=0, column=2, padx=10, sticky="ne")
        middle.grid(row=0, column=3, padx=10, sticky="n")
        extra.grid(row=0, column=4, padx=10, sticky="ne")
        andac.grid(row=0, column=5, padx=10, sticky="ne")

        ttk.Label(middle, text="⚙️ Optionen", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=6, pady=(0, 5), sticky="w")

        ema_row = ttk.Frame(middle)
        ema_row.grid(row=1, column=0, columnspan=6, pady=(0, 8), sticky="w")
        ttk.Label(ema_row, text="Intervall:").pack(side="left")
        ttk.Combobox(
            ema_row,
            textvariable=self.interval,
            values=[
                "1m", "3m", "5m", "10m", "15m", "30m", "45m",
                "1h", "2h", "3h", "4h", "6h", "8h", "12h",
                "1d", "2d", "3d", "1w"
            ],
            width=6
        ).pack(side="left", padx=(4,0))

        multi_row = ttk.Frame(middle)
        multi_row.grid(row=2, column=0, columnspan=6, pady=(0, 8), sticky="w")
        ttk.Label(multi_row, text="Multiplikator:").pack(side="left")
        self.multiplier_entry = ttk.Entry(multi_row, width=8, textvariable=self.multiplier_var)
        self.multiplier_entry.pack(side="left", padx=(4,8))
        ttk.Checkbutton(multi_row, text="Auto", variable=self.auto_multiplier).pack(side="left", padx=(0,8))
        ttk.Label(multi_row, text="Einsatz ($):").pack(side="left", padx=(6,0))
        self.capital_entry = ttk.Entry(multi_row, width=8, textvariable=self.capital_var)
        self.capital_entry.pack(side="left", padx=(4,0))

        time_filter_row = ttk.Frame(middle)
        time_filter_row.grid(row=3, column=0, columnspan=6, pady=(0, 8), sticky="w")
        ttk.Checkbutton(time_filter_row, text="Uhrzeit-Filter", variable=self.use_time_filter).pack(side="left")

        self.time_filters = []
        for i in range(4):
            row = 4 + (i // 2)
            col = i % 2
            label = ttk.Label(middle, text=f"Zeitfenster {i+1}")
            label.grid(row=row*2, column=col, padx=5, pady=(5, 0), sticky="w")
            start = tk.StringVar(value="08:00")
            end = tk.StringVar(value="18:00")
            ttk.Entry(middle, textvariable=start, width=8).grid(row=row*2+1, column=col*2, padx=5)
            ttk.Entry(middle, textvariable=end, width=8).grid(row=row*2+1, column=col*2+1, padx=5)
            self.time_filters.append((start, end))

        extra_row = ttk.Frame(middle)
        extra_row.grid(row=8, column=0, columnspan=6, pady=(0, 8), sticky="w")
        ttk.Checkbutton(
            extra_row,
            text="Nur geschlossene Candles auswerten",
            variable=self.require_closed_candles,
        ).pack(side="left")

        ttk.Label(risk, text="⚠️ Risikomanagement", font=("Arial", 11, "bold")).grid(row=0, column=0, pady=(0, 5), sticky="w")

        apc_frame = ttk.LabelFrame(risk, text="Auto Partial Close")
        apc_frame.grid(row=1, column=0, padx=5, sticky="nw")
        ttk.Checkbutton(apc_frame, text="Aktivieren", variable=self.apc_enabled).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(apc_frame, text="Teilverkaufsrate [%/Intervall]:").grid(row=1, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_rate, width=6).grid(row=1, column=1)
        ttk.Label(apc_frame, text="Intervall [Sekunden]:").grid(row=2, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_interval, width=6).grid(row=2, column=1)
        ttk.Label(apc_frame, text="Mindestgewinn [$]:").grid(row=3, column=0, sticky="w")
        ttk.Entry(apc_frame, textvariable=self.apc_min_profit, width=6).grid(row=3, column=1)
        self.apc_status_label = ttk.Label(apc_frame, text="", foreground="blue")
        self.apc_status_label.grid(row=4, column=0, columnspan=2, sticky="w")

        loss_frame = ttk.LabelFrame(risk, text="Verlust-Limit / Auto-Pause")
        loss_frame.grid(row=2, column=0, padx=5, pady=(10, 0), sticky="nw")
        ttk.Checkbutton(loss_frame, text="Aktivieren", variable=self.max_loss_enabled).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(loss_frame, text="Maximaler Verlust bis Pause [$]:").grid(row=1, column=0, sticky="w")
        ttk.Entry(loss_frame, textvariable=self.max_loss_value, width=8).grid(row=1, column=1)
        self.max_loss_status_label = ttk.Label(loss_frame, text="", foreground="red")
        self.max_loss_status_label.grid(row=3, column=0, columnspan=2, sticky="w")

        manual_frame = ttk.LabelFrame(risk, text="Manuelles SL/TP")
        manual_frame.grid(row=3, column=0, padx=5, pady=(10, 0), sticky="nw")

        risk_frame = ttk.LabelFrame(risk, text="Risikoeinstellungen")
        risk_frame.grid(row=3, column=1, padx=5, pady=(10, 0), sticky="nw")

        ttk.Label(risk_frame, text="Max Risiko pro Trade (%):").grid(row=0, column=0, sticky="w")
        ttk.Entry(risk_frame, textvariable=self.risk_trade_pct, width=6).grid(row=0, column=1)
        ttk.Label(risk_frame, text="Maximaler Drawdown (%):").grid(row=1, column=0, sticky="w")
        ttk.Entry(risk_frame, textvariable=self.max_drawdown_pct, width=6).grid(row=1, column=1)
        ttk.Label(risk_frame, text="Cooldown [Minuten]:").grid(row=2, column=0, sticky="w")
        ttk.Entry(risk_frame, textvariable=self.cooldown_minutes, width=6).grid(row=2, column=1)

        self.toggle_sl_tp_button = ttk.Button(
            manual_frame,
            text="SL/TP AUS",
            command=self.toggle_manual_sl_tp,
        )
        self.toggle_sl_tp_button.grid(row=0, column=0, sticky="w", pady=(5, 0))

        self.sl_tp_hint_label = ttk.Label(
            manual_frame,
            text="❌ Aus: Gegensignal ist dein einziger Exit ⚠️",
            foreground="red",
        )
        self.sl_tp_hint_label.grid(row=0, column=1, columnspan=2, sticky="w")

        ttk.Label(manual_frame, text="SL (%):").grid(row=1, column=0, sticky="w")
        sl_entry = ttk.Entry(manual_frame, textvariable=self.manual_sl_var, width=8)
        sl_entry.grid(row=1, column=1, sticky="w")
        ttk.Button(manual_frame, text="💾", width=3, command=self.save_manual_sl).grid(row=1, column=2, padx=(5, 0))

        ttk.Label(manual_frame, text="TP (%):").grid(row=2, column=0, sticky="w")
        tp_entry = ttk.Entry(manual_frame, textvariable=self.manual_tp_var, width=8)
        tp_entry.grid(row=2, column=1, sticky="w")
        ttk.Button(manual_frame, text="💾", width=3, command=self.save_manual_tp).grid(row=2, column=2, padx=(5, 0))

        self.update_manual_sl_tp_status()

        self._build_andac_options(andac)
        self._build_expert_options(expert_container)
        self._build_controls(self.main_frame)



    def _build_andac_options(self, parent):
        ttk.Label(parent, text="🤑 Entry-Master 🚀", font=("Arial", 11, "bold")).pack(pady=(0, 5))
        options_frame = ttk.Frame(parent)
        options_frame.pack()
        left_col = ttk.Frame(options_frame)
        right_col = ttk.Frame(options_frame)
        left_col.pack(side="left", padx=5, anchor="n")
        right_col.pack(side="left", padx=5, anchor="n")

        for text, var in [
            ("RSI/EMA", self.andac_opt_rsi_ema),
            ("🛡 Sicherheitsfilter", self.andac_opt_safe_mode),
            ("Engulfing", self.andac_opt_engulf),
            ("Engulfing + Breakout", self.andac_opt_engulf_bruch),
            ("Engulfing > ATR", self.andac_opt_engulf_big),
            ("Bestätigungskerze (Delay)", self.andac_opt_confirm_delay),
            ("MTF Bestätigung", self.andac_opt_mtf_confirm),
            ("Starkes Volumen", self.andac_opt_volumen_strong),
            ("Session 7-20 UTC", self.andac_opt_session_filter),
        ]:
            ttk.Checkbutton(left_col, text=text, variable=var).pack(anchor="w")

        self._add_entry_group(right_col, "Lookback", [self.andac_lookback])
        self._add_entry_group(right_col, "Toleranz", [self.andac_puffer])
        self._add_entry_group(right_col, "Volumen-Faktor", [self.andac_vol_mult])

    def _build_expert_options(self, parent):
        ttk.Label(parent, text="⚙️ Experteneinstellungen", font=("Arial", 11, "bold")).pack(pady=(0, 5))
        grid = ttk.Frame(parent)
        grid.pack()

        rows = [
            ("Entry-Cooldown [s]", self.entry_cooldown_seconds),
            ("Cooldown nach Exit [s]", self.cooldown_after_exit),
            ("Max Trades/h", self.max_trades_per_hour),
            ("Gebührensimulation [%]", self.fee_model),
        ]
        for idx, (label, var) in enumerate(rows):
            ttk.Label(grid, text=label+":").grid(row=idx, column=0, sticky="w", pady=2)
            ttk.Entry(grid, textvariable=var, width=10).grid(row=idx, column=1, sticky="w", pady=2)

        sl_frame = ttk.Frame(grid)
        sl_frame.grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(sl_frame, text="SL/TP-Modus:").pack(side="left")
        ttk.Radiobutton(sl_frame, text="Manuell", variable=self.sl_tp_mode, value="manual").pack(side="left")
        ttk.Radiobutton(sl_frame, text="Adaptiv", variable=self.sl_tp_mode, value="adaptive").pack(side="left")

    def _build_controls(self, root):
        button_frame = ttk.Frame(root)
        button_frame.pack(pady=10, fill="x")

        start_btn = ttk.Button(button_frame, text="▶️ Bot starten", command=self.start_bot)
        start_btn.grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="⛔ Trade abbrechen", command=self.emergency_flat_position).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="❗️ Notausstieg", command=self.emergency_exit).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="🛑 Alles stoppen & sichern", command=self.stop_and_reset).grid(row=0, column=3, padx=5)

        auto_chk = ttk.Checkbutton(
            button_frame,
            text="🔁 Auto-Empfehlungen",
            variable=self.auto_apply_recommendations,
            command=self.update_auto_status,
        )
        auto_chk.grid(row=1, column=0, padx=5)
        apply_btn = ttk.Button(button_frame, text="✅ Empfehlungen übernehmen", command=self.apply_recommendations)
        apply_btn.grid(row=1, column=1, padx=5)
        disable_btn = ttk.Button(button_frame, text="🧹 Alles deaktivieren", command=self.disable_all_filters)
        disable_btn.grid(row=1, column=2, padx=5)

        save_btn = ttk.Button(button_frame, text="💾 Einstellungen speichern", command=self.save_to_file)
        save_btn.grid(row=1, column=3, padx=5)

        load_btn = ttk.Button(button_frame, text="⏏️ Einstellungen laden", command=self.load_from_file)
        load_btn.grid(row=1, column=4, padx=5)
        # removed GUI export functionality
        add_gui_diagnose_button(button_frame)

        self.auto_status_label = ttk.Label(button_frame, font=("Arial", 10, "bold"), foreground="green")
        self.auto_status_label.grid(row=2, column=0, columnspan=6, pady=(5, 0), padx=10, sticky="w")

        self.log_box = tk.Text(root, height=13, width=85, wrap="word", bg="#f9f9f9", relief="sunken", borderwidth=2)
        self.log_box.pack(pady=12)

        trade_frame = ttk.LabelFrame(root, text="Letzte Trades und Laufende Position")
        trade_frame.pack(fill="x", padx=5, pady=(0, 10))
        self.trade_box = tk.Text(trade_frame, height=8, width=85, wrap="word", bg="#f0f0f0", relief="sunken", borderwidth=2, state="disabled")
        self.trade_box.pack(fill="both", expand=True)

        ttk.Label(root, textvariable=self.last_reason_var, foreground="red").pack(pady=(0, 5))

    def stop_and_reset(self):
        self.model.should_stop = True
        self.model.running = False
        self.log_event("🧹 Bot gestoppt – Keine Rücksetzung der Konfiguration vorgenommen.")

    def _add_checkbox_entry(self, parent, label, var, entries=[]):
        ttk.Checkbutton(parent, text=label, variable=var).pack(anchor="w")
        for entry_var in entries:
            ttk.Entry(parent, textvariable=entry_var, width=6).pack(anchor="w")

    def _add_entry_group(self, parent, label, entries):
        ttk.Label(parent, text=label).pack()
        for var in entries:
            ttk.Entry(parent, textvariable=var).pack()

    def _build_api_credentials(self, parent):
        self.api_frame = APICredentialFrame(
            parent,
            self.cred_manager,
            log_callback=self.log_event,
        )
        self.api_frame.pack(pady=(0, 10), fill="x")
        for exch in EXCHANGES:
            self.exchange_status_vars[exch] = self.api_frame.status_vars[exch]
            self.exchange_status_labels[exch] = self.api_frame.status_labels[exch]



    def _collect_setting_vars(self):
        self.setting_vars = {
            name: var
            for name, var in vars(self.model).items()
            if isinstance(var, (tk.BooleanVar, tk.StringVar))
        }
        self.setting_vars.update({
            name: var
            for name, var in vars(self).items()
            if isinstance(var, (tk.BooleanVar, tk.StringVar))
        })
        if hasattr(self, "api_frame"):
            for ex, data in self.api_frame.vars.items():
                for key, var in data.items():
                    if isinstance(var, tk.Variable):
                        self.setting_vars[f"api_{ex}_{key}"] = var
            for ex, var in self.api_frame.status_vars.items():
                self.setting_vars[f"api_{ex}_status"] = var
        if hasattr(self, "time_filters"):
            for idx, (start, end) in enumerate(self.time_filters, start=1):
                self.setting_vars[f"time_filter_{idx}_start"] = start
                self.setting_vars[f"time_filter_{idx}_end"] = end

    def _build_status_panel(self):
        self.backend_settings = {}
        self.status_labels = {}
        self.status_rows = {}
        self.logged_errors = set()

        self.system_status_var = tk.StringVar(value="")
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "system_status_label"):
            self.api_frame.system_status_label.config(textvariable=self.system_status_var)

        self.feed_mode_var = tk.StringVar(value="")
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "feed_mode_label"):
            self.api_frame.feed_mode_label.config(textvariable=self.feed_mode_var)

        frame = ttk.Frame(self.root)
        self.all_ok_label = ttk.Label(frame, text="", foreground="green")
        self.all_ok_label.grid(row=0, column=0, sticky="w")
        self.feed_mode_label = ttk.Label(frame, textvariable=self.feed_mode_var, foreground="green")
        self.feed_mode_label.grid(row=0, column=1, padx=(10,0), sticky="w")
        row_index = 1
        for name, var in sorted(self.setting_vars.items()):
            row = ttk.Frame(frame)
            row.grid(row=row_index, column=0, columnspan=2, sticky="w")
            ttk.Label(row, text=name).pack(side="left")
            lbl = ttk.Label(row, text="", foreground="red")
            lbl.pack(side="left", padx=5)
            self.status_rows[name] = row
            self.status_labels[name] = lbl
            var.trace_add("write", lambda *a, n=name, v=var: self.update_setting_status(n, v))
            self.update_setting_status(name, var)
            row_index += 1

        frame.pack_forget()
        self.root.after(1000, self.update_all_status_labels)
        self._update_all_ok_label()

    def update_setting_status(self, name, var):
        try:
            value = var.get()
            parsed = value
            if isinstance(var, tk.BooleanVar):
                parsed = bool(value)
            elif name.startswith("time_filter") or name in {"time_start", "time_end"}:
                datetime.strptime(value, "%H:%M")
            elif isinstance(value, str) and value.replace(".", "", 1).isdigit():
                parsed = float(value) if "." in value else int(value)

            current = self.backend_settings.get(name)
            if parsed != current:
                self.backend_settings[name] = parsed
            active = self.backend_settings.get(name) == parsed
            row = self.status_rows[name]
            label = self.status_labels[name]
            if active:
                row.grid_remove()
            else:
                label.config(text="inaktiv", foreground="red")
                if not row.winfo_ismapped():
                    row.grid()
                self._log_error_once(f"{name} greift nicht")
        except Exception as e:
            row = self.status_rows[name]
            self.status_labels[name].config(text=f"Fehler: {e}", foreground="orange")
            if not row.winfo_ismapped():
                row.grid()
            self._log_error_once(f"{name} Fehler: {e}")
        self._update_all_ok_label()

    def update_all_status_labels(self):
        for name, var in self.setting_vars.items():
            self.update_setting_status(name, var)
        self.root.after(1000, self.update_all_status_labels)
        self._update_all_ok_label()

    def _update_all_ok_label(self):
        any_visible = any(row.winfo_ismapped() for row in self.status_rows.values())
        if any_visible:
            text = "❌ System macht Fehler!"
            color = "red"
        else:
            text = "✅ Alle Systeme laufen fehlerfrei"
            color = "green"

        self.all_ok_label.config(text=text, foreground=color)

        if hasattr(self, "system_status_var"):
            self.system_status_var.set(text)
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "system_status_label"):
            self.api_frame.system_status_label.config(foreground=color)

    def _update_market_monitor(self) -> None:
        # BINANCE_SYMBOL constant moved to andac_entry_master
#         from andac_entry_master import BINANCE_SYMBOL
#         from data_provider import fetch_last_price, WebSocketStatus

        symbol = BINANCE_SYMBOL
        price = fetch_last_price()
        self.model.websocket_active = WebSocketStatus.is_running()

        stamp = datetime.now().strftime("%H:%M:%S")
        line = (
            f"{symbol.replace('_','')}: {price:.2f} ({stamp})" if price is not None else f"{symbol}: ❌ ({stamp})"
        )
        if hasattr(self, "api_frame") and hasattr(self.api_frame, "log_price"):
            self.api_frame.log_price(line, error=price is None)
        if price is not None:
            self.update_feed_status(True)
        else:
            self.update_feed_status(False, "Keine Marktdaten – bitte prüfen")

        self.root.after(self.market_interval_ms, self._update_market_monitor)

    def update_trade_display(self):
        if not self.trade_box:
            return

        lines = []
        if self.current_position:
            direction = self.current_position.get("direction")
            entry = self.current_position.get("entry_price")
            bars = self.current_position.get("bars_open", 0)
            lines.append(f"\U0001F4CA Laufende Position: {direction} @ {entry:.2f} | seit {bars} Kerzen")
        else:
            lines.append("\U0001F4CA Laufende Position: ---")

        lines.append("")
        lines.append("\U0001F4DC Letzte Trades:")
        for trade in reversed(self.trade_history[-5:]):
            lines.append(
                f"[{trade['timestamp']}] {trade['direction']} @ {trade['entry']:.2f} → {trade['exit']:.2f} = {trade['pnl']:+.2f}$ ({trade['percent']:+.2f}%)"
            )

        self.trade_box.config(state="normal")
        self.trade_box.delete("1.0", "end")
        self.trade_box.insert("end", "\n".join(lines))
        self.trade_box.config(state="disabled")

    def update_last_trade(self, side: str, entry: float, exit_price: float, pnl: float):
        super().update_last_trade(side, entry, exit_price, pnl)
        pct = 0.0
        try:
            if side.lower() == "long":
                pct = (exit_price - entry) / entry * 100
            else:
                pct = (entry - exit_price) / entry * 100
        except Exception:
            pct = 0.0

        stamp = datetime.now().strftime("%H:%M:%S")
        self.trade_history.append(
            {
                "timestamp": stamp,
                "direction": side.upper(),
                "entry": entry,
                "exit": exit_price,
                "pnl": pnl,
                "percent": pct,
            }
        )
        self.update_trade_display()




# === from gui_bridge.py ===
# gui_bridge.py

# Bridge to interact with configuration stored in EntryMasterBot
# from andac_entry_master import EntryMasterBot
import logging

def smart_auto_multiplier(score, atr, balance, drawdown, max_risk_pct=1.0, base_multi=20, min_multi=1, max_multi=50):
    """Return a leverage suggestion based on score, ATR and drawdown."""
    score_factor = 1.0 + max(0, (score - 0.7) * 2)
    atr_factor = max(0.5, min(1.2, 30 / (atr + 1)))
    dd_factor = 1.0 if drawdown < 0.1 else 0.5

    smart_multi = base_multi * score_factor * atr_factor * dd_factor
    smart_multi = min(max(smart_multi, min_multi), max_multi)

    return round(smart_multi, 2)

class GUIBridge:
    def __init__(self, gui_instance=None, bot: EntryMasterBot | None = None):
        self.gui = gui_instance
        self.model = getattr(gui_instance, "model", None)
        self.bot = bot or EntryMasterBot()

    def update_params(
        self,
        multiplier: float,
        auto_multi: bool,
        capital: float,
        interval: str,
        risk_pct: float | None = None,
        drawdown_pct: float | None = None,
        cooldown: int | None = None,
    ) -> None:
        """Store trading parameters from the GUI into bot settings."""
        params = {
            "multiplier": multiplier,
            "auto_multiplier": auto_multi,
            "capital": capital,
            "interval": interval,
        }
        if risk_pct is not None:
            params["risk_per_trade"] = risk_pct
        if drawdown_pct is not None:
            params["drawdown_pct"] = drawdown_pct
        if cooldown is not None:
            params["cooldown"] = cooldown
        self.bot.apply_settings(params)

    def _get_gui_value(self, name: str, fallback):
        if not self.gui or not hasattr(self.gui, name):
            return fallback
        try:
            return type(fallback)(getattr(self.gui, name).get())
        except Exception:
            return fallback

    def get_leverage(self, score=0.8, atr=25, balance=1000, drawdown=0.0):  # UNUSED
        """Calculate leverage recommendation. Currently unused."""
        if self.auto_multiplier:
            return smart_auto_multiplier(
                score=score,
                atr=atr,
                balance=balance,
                drawdown=drawdown,
            )
        return self.multiplier

    @property
    def multiplier(self):
        return self._get_gui_value("multiplier_entry", self.bot.settings.get("multiplier", 20))

    @property
    def auto_multiplier(self):
        return self._get_gui_value("auto_multiplier", self.bot.settings.get("auto_multiplier", False))

    @property
    def capital(self):
        return self._get_gui_value("capital_entry", self.bot.settings.get("capital", 1000))

    @property
    def interval(self):
        return self._get_gui_value("interval", self.bot.settings.get("interval", "15m"))

    @property
    def live_trading(self):
        return self._get_gui_value("live_trading", not self.bot.settings.get("paper_mode", True))


    @property
    def manual_sl(self):
        return self._get_gui_value("manual_sl_var", None)

    @property
    def manual_tp(self):
        return self._get_gui_value("manual_tp_var", None)

    @property
    def manual_active(self):
        return self._get_gui_value("sl_tp_manual_active", False)

    @property
    def auto_active(self):
        return self._get_gui_value("sl_tp_auto_active", False)

    def set_manual_status(self, ok: bool):
        if self.gui and hasattr(self.gui, "set_manual_sl_status"):
            self.gui.set_manual_sl_status(ok)

    def set_auto_status(self, ok: bool):
        if self.gui and hasattr(self.gui, "set_auto_sl_status"):
            self.gui.set_auto_sl_status(ok)



    def update_live_pnl(self, pnl):
        if self.gui:
            self.gui.update_live_trade_pnl(pnl)

    def update_capital(self, capital, saved):
        if self.gui:
            self.gui.update_capital(capital, saved)

    def log_event(self, msg):
        if self.gui:
            self.gui.log_event(msg)

    def update_status(self, msg):
        if self.gui and hasattr(self.gui, "auto_status_label"):
            self.gui.auto_status_label.config(text=msg)

    def stop_bot(self):
        if self.gui:
            self.gui.running = False

    def update_filter_feedback(self, score):  # UNUSED
        """Placeholder for GUI feedback based on filter score."""
        return

    # REMOVED: SessionFilter configuration

    def update_filter_params(self):
        def get_safe_float(var, default=0.0):
            try:
                return float(var.get())
            except Exception:
                return default

        def get_safe_int(var, default=0):
            try:
                return int(var.get())
            except Exception:
                return default

        if not self.model:
            logging.debug("🔁 Dummy update_filter_params aufgerufen (GUIBridge)")
            return

        lookback_var = getattr(self.model, "lookback_var", None)
        toleranz_var = getattr(self.model, "toleranz_var", None)
        volume_var = getattr(self.model, "volume_var", None)
        breakout_var = getattr(self.model, "breakout_var", None)

        self.bot.apply_settings({
            "lookback": get_safe_int(lookback_var, 3),
            "toleranz": get_safe_float(toleranz_var, 0.01),
            "min_volume": get_safe_float(volume_var, 0.0),
            "breakout_only": breakout_var.get() if breakout_var else False,
        })




# === from console_status.py ===
# console_status.py

import time
from datetime import datetime

_last_warnings = {}
_last_options_snapshot = {}

def _throttle_warn(key, seconds=30):
    now = time.time()
    last = _last_warnings.get(key, 0)
    if now - last > seconds:
        _last_warnings[key] = now
        return True
    return False

def print_full_filter_overview(settings):  # UNUSED
    """Print a table of all filter settings to the console."""
    groups = [
        ("RSI", settings.get("rsi_filter", False)),
        ("Volume", settings.get("volume_filter", False)),
        ("EMA", settings.get("ema_filter", False)),
        ("TrailingSL", settings.get("trailing_sl", False)),
        ("Doji", settings.get("doji_filter", False)),
        ("Engulfing", settings.get("engulfing_filter", False)),
        ("BigMove", settings.get("big_move_filter", False)),
        ("Breakout", settings.get("breakout_filter", False)),
        ("TimeFilter", settings.get("time_filter", False)),
        ("ATR-Filter", settings.get("atr_filter", False)),
        ("Momentum", settings.get("momentum_filter", False)),
        ("Wick", settings.get("wick_filter", False)),
        ("Rejection", settings.get("rejection_filter", False)),
        ("ReEntry", settings.get("reentry_filter", False)),
        ("SL-Intelligenz", settings.get("sl_intel", False)),
        ("CapitalSafe", settings.get("capital_safe", False)),
        ("SessionBlock", settings.get("session_block", False)),
        ("EntryMaster", settings.get("entry_master", False)),
        ("AdaptiveSL", settings.get("adaptive_sl", False)),
    ]
    print("🛠 Filter- & Optionen-Status:")
    for i, (name, active) in enumerate(groups):
        status = "✅" if active else "❌"
        print(f"{name:16}: {status}", end="   ")
        if (i + 1) % 4 == 0:
            print("")
    print("\n")

def options_snapshot(settings):  # UNUSED
    """Return the current on/off state of all filter options."""
    keys = (
        "rsi_filter", "volume_filter", "ema_filter", "trailing_sl",
        "doji_filter", "engulfing_filter", "big_move_filter",
        "breakout_filter", "time_filter", "atr_filter", "momentum_filter", "wick_filter",
        "rejection_filter", "reentry_filter", "sl_intel", "capital_safe",
        "session_block", "entry_master", "adaptive_sl"
    )
    return tuple(settings.get(k) for k in keys)

def print_no_signal_status(settings, position=None, price=None, session_name=None, saved_profit=None, only_active_filters=True):  # UNUSED
    """Output detailed status information when no entry signal is present."""
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    print(f"{nowstr} ➖ Ich warte auf ein Indikator Signal" + (f" | Session: {session_name}" if session_name else ""))
    filter_status = []
    filter_status.append("RSI✅" if settings.get("rsi_filter", False) else "RSI❌")
    filter_status.append("Volume✅" if settings.get("volume_filter", False) else "Volume❌")
    filter_status.append("EMA✅" if settings.get("ema_filter", False) else "EMA❌")
    filter_status.append("TrailingSL✅" if settings.get("trailing_sl", False) else "TrailingSL❌")
    filter_status.append("Doji✅" if settings.get("doji_filter", False) else "Doji❌")
    filter_status.append("Engulfing✅" if settings.get("engulfing_filter", False) else "Engulfing❌")
    filter_status.append("BigMove✅" if settings.get("big_move_filter", False) else "BigMove❌")
    filter_status.append("Breakout✅" if settings.get("breakout_filter", False) else "Breakout❌")
    filter_status.append("TimeFilter✅" if settings.get("time_filter", False) else "TimeFilter❌")
    filter_status.append("ATR-Filter✅" if settings.get("atr_filter", False) else "ATR-Filter❌")
    filter_status.append("Momentum✅" if settings.get("momentum_filter", False) else "Momentum❌")
    filter_status.append("Wick✅" if settings.get("wick_filter", False) else "Wick❌")
    filter_status.append("Rejection✅" if settings.get("rejection_filter", False) else "Rejection❌")
    filter_status.append("ReEntry✅" if settings.get("reentry_filter", False) else "ReEntry❌")
    filter_status.append("SL-Intelligenz✅" if settings.get("sl_intel", False) else "SL-Intelligenz❌")
    filter_status.append("CapitalSafe✅" if settings.get("capital_safe", False) else "CapitalSafe❌")
    filter_status.append("SessionBlock✅" if settings.get("session_block", False) else "SessionBlock❌")
    filter_status.append("EntryMaster✅" if settings.get("entry_master", False) else "EntryMaster❌")
    filter_status.append("AdaptiveSL✅" if settings.get("adaptive_sl", False) else "AdaptiveSL❌")

    if only_active_filters:
        active = [f.replace("✅", "") for f in filter_status if "✅" in f]
        filters_text = " | ".join(active) if active else "Keine aktiven Filter"
        print("🎛 Aktive Filter:", filters_text)
    else:
        print("🎛 Filter/Optionen:", " | ".join(filter_status))

    sl = tp = "-"
    if position:
        sl = f"{position.get('sl', '-'):.2f}" if position.get('sl') is not None else "-"
        tp = f"{position.get('tp', '-'):.2f}" if position.get('tp') is not None else "-"
    balance = settings.get("starting_balance", "-")
    leverage = settings.get("leverage", "-")
    symbol = settings.get("symbol", "-")
    if price is None:
        price = "-"
    print(f"💵 Balance: {balance} | 💎 Gespart: {saved_profit if saved_profit is not None else '-'} | 📈 {symbol} Preis: {price} | 🎯 SL: {sl} | TP: {tp} | Lev: x{leverage}")
    print("")

def print_entry_status(position, settings):  # UNUSED
    """Log entry details to the console."""
    direction = position.get("direction", position.get("side", "?"))
    entry = position.get("entry", "-")
    sl = position.get("sl", "-")
    tp = position.get("tp", "-")
    symbol = position.get("symbol", settings.get("symbol", "-"))
    print(f"🚀 {symbol} ENTRY ({direction.upper()}): Entry {entry} | SL {sl} | TP {tp}")
    print("")

def print_position_status(position, price, session_name=None):  # UNUSED
    """Show current position and SL/TP on console."""
    direction = position.get("direction", position.get("side", "?"))
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    session_txt = f" | Session: {session_name}" if session_name else ""
    print(f"{nowstr} ⏳ Position offen ({direction}) | Entry: {position['entry']:.2f} | Now: {price:.2f}{session_txt}")
    print(f"🎯 SL: {position['sl']:.2f} | TP: {position['tp']:.2f}")
    print("")

def print_pnl_status(pnl, balance=None, saved=None):  # UNUSED
    """Print current PnL with optional balance information."""
    msg = f"📉 PnL: {pnl:.2f} $"
    if balance is not None:
        msg += f" | 💰 Balance: {balance:.2f}"
    if saved is not None:
        msg += f" | 💎 Gespart: {saved:.2f}"
    print(msg)
    print("")

def print_trade_closed(position, price, pnl, saved_profit=None, duration=None, session_name=None):  # UNUSED
    """Output trade closing information to the console."""
    direction = position.get("direction", position.get("side", "?")).upper()
    symbol = position.get("symbol", "-")
    entry = position.get("entry", "-")
    sl = position.get("sl", "-")
    tp = position.get("tp", "-")
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    session_txt = f" | Session: {session_name}" if session_name else ""
    print(f"{nowstr} 💥 Trade EXIT ({direction}) {symbol}")
    print(f"Entry: {entry} | Exit: {price} | SL: {sl} | TP: {tp}")
    print(f"📉 Gewinn: {pnl:+.2f} $ | 💎 Gespart: {saved_profit if saved_profit is not None else '-'}"
          + (f" | Dauer: {duration}min" if duration else "") + session_txt)
    print("")

def print_error(msg, exception=None):  # UNUSED
    """Display an error message."""
    print(f"❌ Fehler: {msg}")
    if exception:
        print(str(exception))
    print("")

def print_warning(msg, warn_key="default", seconds=30):
    if _throttle_warn(warn_key, seconds):
        print(f"⚠️ {msg}")
        print("")

def print_info(msg):  # UNUSED
    """Display an informational message."""
    print(f"ℹ️ {msg}")
    print("")

def print_start_banner(start_balance, saved_profit=None):
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    print(f"{nowstr} 🚀 Bot gestartet")
    print(
        f"🧾 Startkapital: ${start_balance:.2f}"
        + (f" | 💎 Gespart: {saved_profit}" if saved_profit else "")
    )
    print("")

def print_stop_banner(reason: str | None = None) -> None:
    nowstr = datetime.now().strftime("[%H:%M:%S]")
    msg = f"{nowstr} 🛑 Bot gestoppt"
    if reason:
        msg += f" – {reason}"
    print(msg)
    print("")

def print_settings_overview(settings):
    print_full_filter_overview(settings)



# === from status_block.py ===
# status_block.py

import time
from datetime import datetime, timedelta
from colorama import Style
# from global_state import atr_value_global, ema_trend_global

def get_entry_status_text(position: dict, capital, app, leverage: int, settings: dict) -> str:
    from datetime import timedelta
    from colorama import Style

    side = position["side"]
    color = "🟢" if side == "long" else "🔴"
    entry_time = position.get("entry_time")
    runtime = int(time.time() - entry_time) if entry_time else 0
    runtime_str = str(timedelta(seconds=runtime))
    now = datetime.now()
    uhrzeit = now.strftime("%H:%M:%S")
    datum = now.strftime("%d.%m.%Y")
    einsatz = float(position.get("amount", capital))
    entry_price = float(position["entry"])
    atr = float(atr_value_global) if atr_value_global is not None else 0.0
    ema_trend = ema_trend_global
    modus = "🚀 Modus: LIVE"
    trade_info = f"{side.upper()} @ {entry_price:.2f}"
    pnl = 0.0

    lev_str = f"x{int(leverage)}" if leverage == int(leverage) else f"x{leverage:.2f}"

    filters = {
        "RSI/EMA": app.andac_opt_rsi_ema.get(),
        "SAFE": app.andac_opt_safe_mode.get(),
        "ENG": app.andac_opt_engulf.get(),
        "BRUCH": app.andac_opt_engulf_bruch.get(),
        "BIG": app.andac_opt_engulf_big.get(),
        "DELAY": app.andac_opt_confirm_delay.get(),
        "MTF": app.andac_opt_mtf_confirm.get(),
        "VOL": app.andac_opt_volumen_strong.get(),
    }
    filter_line = "🎛 Andac: " + "  ".join(f"{k}{'✅' if v else '❌'}" for k, v in filters.items())

    lines = [
        f"{color} {trade_info} | 💼 ${einsatz:.2f} | {lev_str}",
        f"PnL: ${pnl:.2f} | Laufzeit: {runtime_str} | ⏰ {uhrzeit} | 📅 {datum}",
        f"📉 ATR: ${atr:.2f} | 📈 EMA: {ema_trend} | {modus}",
        "",
        filter_line,
        Style.RESET_ALL
    ]
    return "\n".join(lines)

def print_entry_status(position: dict, capital, app, leverage: int, settings: dict):
    print(get_entry_status_text(position, capital, app, leverage, settings))


# === from system_monitor.py ===
# system_monitor.py

# from __future__ import annotations

from datetime import datetime
import threading
import time
from typing import Optional

# from status_events import StatusDispatcher
import logging
# import global_state


def _beep() -> None:
    try:
        print("\a", end="", flush=True)  # CLEANUP: simple console beep
    except Exception:
        pass


class SystemMonitor:

    def __init__(self, gui, interval: int = 2, timeout: int = 10) -> None:
        self.gui = gui
        self.interval = max(1, interval)
        self.timeout = timeout
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._feed_ok = True
        self._pause_reason: Optional[str] = None
        self._last_checked_ts: Optional[float] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    def _log(self, msg: str) -> None:
#         from central_logger import log_messages

        for line in log_messages(msg):
            stamp = datetime.now().strftime("[%H:%M:%S]")
            full = f"{stamp} {line}"
            if hasattr(self.gui, "log_event"):
                self.gui.log_event(full)
            else:
                logging.getLogger(__name__).info(full)

    def _run(self) -> None:
        while self._running:
            try:
                ts = global_state.last_feed_time
                if ts == self._last_checked_ts:
                    time.sleep(self.interval)
                    continue
                self._last_checked_ts = ts
                if ts is None:
                    self._handle_feed_down("Keine Marktdaten empfangen")
                elif time.time() - ts > 30:
                    self._handle_feed_down("Marktdaten aktualisieren sich nicht")
                else:
                    self._handle_feed_up()
            except Exception as exc:
                info = f"{type(exc).__name__}: {exc}"
                logging.debug("Systemmonitor exception: %s", info)
                self._handle_feed_down("API-Fehler – Antwort unvollständig", log=False)
            time.sleep(self.interval)


    def _handle_feed_down(self, reason: str, *, log: bool = True) -> None:
        if self._feed_ok:
            _beep()
            if log:
                self._log(f"{reason} – Bot pausiert")
            if hasattr(self.gui, "update_feed_status"):
                self.gui.update_feed_status(False, reason)
            StatusDispatcher.dispatch("feed", False, reason)
            if getattr(self.gui, "running", False):
                self.gui.running = False
                self._pause_reason = "feed"
        self._feed_ok = False

    def _handle_feed_up(self) -> None:
        if not self._feed_ok and not getattr(self.gui, "running", False) and self._pause_reason == "feed":
            self.gui.running = True
        self._pause_reason = None
        if hasattr(self.gui, "update_feed_status"):
            self.gui.update_feed_status(True)
        StatusDispatcher.dispatch("feed", True)
        self._feed_ok = True


# === from feed_delay_monitor.py ===
# ADDED: monitor feed delay to detect lag
"""Simple timer-based feed delay monitor."""

import threading
import time
import logging
# import global_state
from queue import Queue
# from status_events import StatusDispatcher


def start(interval: int, queue_obj: Queue | None = None) -> None:
    """Start monitoring feed delays."""
    def _run():
        while True:
            last = global_state.last_feed_time
            if last and time.time() - last > interval:
                logging.warning(
                    "⚠️ Feed überlastet – Verzögerung %.1fs", time.time() - last
                )
            if queue_obj is not None and queue_obj.qsize() > 10:
                logging.warning("⚠️ Feed-Stau: Queue > 10")
                StatusDispatcher.dispatch("feed", False, "Queue>10")
            time.sleep(interval // 2)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


# === from feed_simulator.py ===
# feed_simulator.py
"""Offline candle feed for strategy testing."""

# from __future__ import annotations

import csv
import json
import time
from typing import Callable, Iterable, Iterator, Dict


class FeedSimulator:
    """Load candles from file and feed them sequentially."""

    def __init__(self, filename: str) -> None:
        self.filename = filename

    def _read_json(self) -> Iterator[Dict[str, float]]:
        with open(self.filename, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    def _read_csv(self) -> Iterator[Dict[str, float]]:
        with open(self.filename, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k: float(v) if k != "timestamp" else int(v) for k, v in row.items()}
                yield row

    def candles(self) -> Iterable[Dict[str, float]]:
        if self.filename.lower().endswith(".json"):
            return self._read_json()
        return self._read_csv()

    def run(self, callback: Callable[[Dict[str, float]], None], delay: float = 0.0) -> None:
        """Send each candle to *callback* with optional delay in seconds."""
        for candle in self.candles():
            callback(candle)
            if delay > 0:
                time.sleep(delay)


# === from andac_entry_master.py ===
# andac_entry_master.py

# from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Callable, Any
import json
import time
import threading
import queue

# ---------------------------------------------------------------------------
# Consolidated defaults (from config.py)
BINANCE_SYMBOL = "BTCUSDT"
BINANCE_INTERVAL = "1m"
SETTINGS = {
    "symbol": BINANCE_SYMBOL,
    "interval": BINANCE_INTERVAL,
    "starting_balance": 2000,
    "leverage": 10,
    "stop_loss_atr_multiplier": 0.75,
    "take_profit_atr_multiplier": 1.5,
    "multiplier": 10,
    "auto_multiplier": False,
    "capital": 2000,
    "version": "V10.4_Pro",
    "paper_mode": True,
    "data_source_mode": "websocket",
    "auto_partial_close": True,
    "partial_close_pct": 0.25,
    "apc_min_profit": 20,
    "risk_per_trade": 3.0,
    "drawdown_pct": 15.0,
    "max_drawdown": 300,
    "max_loss": 60,
    "cooldown": 2,
    "cooldown_after_exit": 120,
    "sl_tp_mode": "adaptive",
    "opt_session_filter": False,
    "sl_tp_manual_active": True,
    "manual_sl": 0.75,
    "manual_tp": 1.5,
}




@dataclass
class AndacSignal:

    signal: Optional[str]
    rsi: float
    vol_spike: bool
    engulfing: bool
    reasons: List[str] = field(default_factory=list)


class AndacEntryMaster:

    def __init__(
        self,
        lookback: int = 20,
        puffer: float = 10.0,
        vol_mult: float = 1.2,
        opt_tpsl: bool = True,
        opt_rsi_ema: bool = False,
        opt_safe_mode: bool = False,
        opt_engulf: bool = False,
        opt_engulf_bruch: bool = False,
        opt_engulf_big: bool = False,
        opt_confirm_delay: bool = False,
        opt_mtf_confirm: bool = False,
        opt_volumen_strong: bool = False,
        opt_session_filter: bool = False,
        cooldown: Optional[int] = None,
        max_drawdown_pct: Optional[float] = None,
        max_loss: Optional[float] = None,
        sl_tp_manual_active: Optional[bool] = None,
    ) -> None:
        self.lookback = lookback
        self.puffer = puffer
        self.vol_mult = vol_mult
        self.opt_tpsl = opt_tpsl
        self.opt_rsi_ema = opt_rsi_ema
        self.opt_safe_mode = opt_safe_mode
        self.opt_engulf = opt_engulf
        self.opt_engulf_bruch = opt_engulf_bruch
        self.opt_engulf_big = opt_engulf_big
        self.opt_confirm_delay = opt_confirm_delay
        self.opt_mtf_confirm = opt_mtf_confirm
        self.opt_volumen_strong = opt_volumen_strong
        self.opt_session_filter = opt_session_filter

        self.cooldown = cooldown if cooldown is not None else SETTINGS.get("cooldown", 0)
        self.max_drawdown_pct = (
            max_drawdown_pct if max_drawdown_pct is not None else SETTINGS.get("drawdown_pct", 0.0)
        )
        self.max_loss = max_loss if max_loss is not None else SETTINGS.get("max_loss", 0.0)
        self.sl_tp_manual_active = (
            sl_tp_manual_active if sl_tp_manual_active is not None else SETTINGS.get("sl_tp_manual_active", True)
        )

        self.candles: List[Dict[str, float]] = []
        self.prev_bull_signal = False
        self.prev_bear_signal = False
        self.last_signal_time = 0.0
        self.current_drawdown = 0.0
        self.daily_loss = 0.0
        self.last_block_reason: Optional[str] = None

    @staticmethod
    def _sma(values: List[float], length: int) -> float:
        if len(values) < length:
            return sum(values) / len(values)
        return sum(values[-length:]) / length

    @staticmethod
    def _highest(values: List[float], length: int) -> float:
        slice_ = values[-length:] if len(values) >= length else values
        return max(slice_)

    @staticmethod
    def _lowest(values: List[float], length: int) -> float:
        slice_ = values[-length:] if len(values) >= length else values
        return min(slice_)

    @staticmethod
    def _atr(candles: List[Dict[str, float]], length: int) -> float:
        if len(candles) < length + 1:
            return 0.0
        trs = []
        for i in range(-length, 0):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs) / length

    @staticmethod
    def _rsi(closes: List[float], length: int) -> float:
        if len(closes) < length + 1:
            return 50.0
        gains = []
        losses = []
        for i in range(1, length + 1):
            diff = closes[-i] - closes[-i - 1]
            if diff >= 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        avg_gain = sum(gains) / length if gains else 0
        avg_loss = sum(losses) / length if losses else 0.000001
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        return max(0.0, min(100.0, rsi))

    def is_trade_allowed(self) -> tuple[bool, Optional[str]]:
        now = time.time()
        if now - self.last_signal_time < self.cooldown:
            self.last_block_reason = "cooldown"
            return False, "cooldown"
        if (
            self.current_drawdown >= self.max_drawdown_pct
            or self.daily_loss >= self.max_loss
        ):
            self.last_block_reason = "drawdown block"
            return False, "drawdown block"
        if not self.sl_tp_manual_active:
            self.last_block_reason = "sl/tp disabled"
            return False, "sl/tp disabled"
        self.last_block_reason = None
        return True, None

    def evaluate(self, candle: Dict[str, float], symbol: str = "BTCUSDT") -> AndacSignal:

        self.candles.append(candle)
        if len(self.candles) > self.lookback + 20:
            self.candles.pop(0)
        if len(self.candles) < self.lookback + 2:
            return AndacSignal(None, 50.0, False, False)

        allowed, reason = self.is_trade_allowed()
        if not allowed:
            return AndacSignal(None, 50.0, False, False, [reason])

        highs = [c["high"] for c in self.candles]
        lows = [c["low"] for c in self.candles]
        volumes = [c.get("volume", 0.0) for c in self.candles]
        closes = [c["close"] for c in self.candles]

        hoch_vorher = self._highest(highs[:-1], self.lookback)
        tief_vorher = self._lowest(lows[:-1], self.lookback)

        bruch_oben = candle["high"] > hoch_vorher + self.puffer
        bruch_unten = candle["low"] < tief_vorher - self.puffer

        vol_schnitt = self._sma(volumes[:-1], self.lookback)
        atr = self._atr(self.candles[:-1], 14)
        big_candle = abs(candle["close"] - candle["open"]) > atr
        vol_spike = candle["volume"] > vol_schnitt * self.vol_mult and big_candle
        if self.opt_volumen_strong:
            vol_spike = vol_spike and candle["volume"] > vol_schnitt * 1.5

        rsi = self._rsi(closes, 14)

        session_ok = not self.opt_session_filter or 7 <= datetime.utcnow().hour <= 20

        mtf_ok = True
        if self.opt_mtf_confirm:
            mtf_ok = True

        prev = self.candles[-2]
        bull_eng = (
            candle["close"] > candle["open"]
            and prev["close"] < prev["open"]
            and candle["close"] > prev["open"]
            and candle["open"] < prev["close"]
        )
        bear_eng = (
            candle["close"] < candle["open"]
            and prev["close"] > prev["open"]
            and candle["close"] < prev["open"]
            and candle["open"] > prev["close"]
        )
        eng_long_ok = bull_eng and (not self.opt_engulf_bruch or bruch_oben) and (
            not self.opt_engulf_big or big_candle
        )
        eng_short_ok = bear_eng and (not self.opt_engulf_bruch or bruch_unten) and (
            not self.opt_engulf_big or big_candle
        )

        reasons_long: List[str] = []
        reasons_short: List[str] = []

        candidate_long = bruch_oben and vol_spike
        candidate_short = bruch_unten and vol_spike

        if candidate_long:
            if self.opt_rsi_ema and rsi <= 50:
                reasons_long.append(f"RSI {rsi:.1f} <= 50")
            if self.opt_safe_mode and rsi <= 30:
                reasons_long.append(f"RSI {rsi:.1f} <= 30 (Safe)")
            if self.opt_engulf and not eng_long_ok:
                reasons_long.append("Engulfing")
            if self.opt_session_filter and not session_ok:
                reasons_long.append("Session")
            if self.opt_mtf_confirm and not mtf_ok:
                reasons_long.append("MTF")
            if self.opt_confirm_delay and not (
                self.prev_bull_signal and candle["close"] > candle["open"]
            ):
                reasons_long.append("Confirm")

        if candidate_short:
            if self.opt_safe_mode and rsi >= 70:
                reasons_short.append(f"RSI {rsi:.1f} >= 70 (Safe)")
            if self.opt_engulf and not eng_short_ok:
                reasons_short.append("Engulfing")
            if self.opt_session_filter and not session_ok:
                reasons_short.append("Session")
            if self.opt_mtf_confirm and not mtf_ok:
                reasons_short.append("MTF")
            if self.opt_confirm_delay and not (
                self.prev_bear_signal and candle["close"] < candle["open"]
            ):
                reasons_short.append("Confirm")

        bull_final = candidate_long and not reasons_long
        bear_final = candidate_short and not reasons_short

        self.prev_bull_signal = candidate_long
        self.prev_bear_signal = candidate_short

        signal = None
        reasons: List[str] = []
        if bull_final:
            signal = "long"
        elif bear_final:
            signal = "short"
        else:
            if candidate_long:
                reasons = reasons_long
            elif candidate_short:
                reasons = reasons_short

        if signal:
            self.last_signal_time = time.time()
        engulfing = bull_eng if signal == "long" else bear_eng if signal == "short" else False
        return AndacSignal(signal, rsi, vol_spike, engulfing, reasons)


# ---------------------------------------------------------------------------
# Helper indicator functions (from indicator_utils.py)
def calculate_ema(values: List[float], length: int, round_result: bool = False):
    if not values or len(values) < length:
        return None
    k = 2 / (length + 1)
    ema = values[0]
    for price in values[1:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2) if round_result else ema


def calculate_rsi(close: float, low: float, high: float) -> float:
    if high - low == 0:
        return 50
    midpoint = (high + low) / 2
    relative = (close - midpoint) / (high - low)
    rsi = 50 + (relative * 50)
    return max(0, min(100, rsi))


def calculate_atr(candles: List[Dict[str, float]], length: int) -> float:
    candles = [
        c for c in candles if all(k in c and c[k] is not None for k in ("high", "low", "close"))
    ]
    if not candles or len(candles) < length:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return round(sum(trs[-length:]) / length, 2)


def calculate_volatility_score(candle: Dict[str, float], atr: float) -> float:
    candle_range = candle["high"] - candle["low"]
    return round(candle_range / atr, 2) if atr else 0


def macd_crossover_detected(closes: List[float], short: int = 12, long: int = 26, signal: int = 9) -> bool:
    if len(closes) < long + signal + 1:
        return False

    def ema(values: List[float], length: int) -> float:
        k = 2 / (length + 1)
        e = values[0]
        for price in values[1:]:
            e = price * k + e * (1 - k)
        return e

    prev = closes[-(long + signal + 1):-1]
    curr = closes[-(long + signal):]

    prev_macd = ema(prev, short) - ema(prev, long)
    curr_macd = ema(curr, short) - ema(curr, long)
    prev_signal = ema([prev_macd], signal)
    curr_signal = ema([prev_macd, curr_macd], signal)

    return (prev_macd < prev_signal and curr_macd > curr_signal) or (
        prev_macd > prev_signal and curr_macd < curr_signal
    )


# ---------------------------------------------------------------------------
# AdaptiveSLManager (from adaptive_sl_manager.py)
class AdaptiveSLManager:
    def __init__(self, atr_period: int = 14) -> None:
        self.atr_period = atr_period

    def calculate_atr(self, candles: List[Dict[str, float]]) -> float:
        if len(candles) < self.atr_period + 1:
            raise ValueError(f"Mindestens {self.atr_period+1} Kerzen f\xC3\xBCr ATR-Berechnung n\xC3\xB6tig.")
        trs = []
        for i in range(-self.atr_period, 0):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        atr = float(sum(trs) / len(trs))
        if atr < 1e-5:
            raise ValueError("ATR zu klein oder ung\xC3\xBCltig")
        return atr

    def get_adaptive_sl_tp(self, direction: str, entry_price: float, candles: List[Dict[str, float]]):
        direction = direction.lower()
        if direction not in ("long", "short"):
            raise ValueError("Richtung muss 'long' oder 'short' sein.")
        atr = self.calculate_atr(candles)
        if direction == "long":
            sl = entry_price - atr
            tp = entry_price + atr
        else:
            sl = entry_price + atr
            tp = entry_price - atr
        return float(sl), float(tp)



# ---------------------------------------------------------------------------
# Entry/Exit handler wrappers (from entry_handler.py & exit_handler.py)
def open_position(side: str, quantity: float, reduce_only: bool = False, order_type: str = "Market") -> Optional[dict]:
    try:
        return bm_place_order(side, quantity, reduce_only=reduce_only, order_type=order_type)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("open_position failed: %s", exc)
        return None


def close_position() -> Optional[dict]:
    try:
        return bm_close_position()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("close_position failed: %s", exc)
        return None


def close_partial_position(volume: float, order_type: str = "Market") -> Optional[dict]:
    if volume <= 0:
        return None
    try:
        position = bm_get_open_position()
        if not position:
            return None
        side = "Sell" if position["currentQty"] > 0 else "Buy"
        return bm_place_order(side, abs(volume), reduce_only=True, order_type=order_type)
    except Exception:
        return None


# BaseWebSocket & BinanceCandleWebSocket
class BaseWebSocket:
    def __init__(self, url: str, on_message: Callable) -> None:
        self.url = url
        self.on_message = on_message
        self.ws: Optional[Any] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False

    def _run(self) -> None:
        time.sleep(2)
        while self._running:
            try:
                from websocket import WebSocketApp
                self.ws = WebSocketApp(self.url, on_message=self.on_message)
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception:
                time.sleep(5)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self) -> None:
        self._running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)


class BinanceCandleWebSocket(BaseWebSocket):
    def __init__(self, on_candle: Optional[Callable[[dict], None]] = None, interval: str | None = None) -> None:
        self.on_candle = on_candle
        self.symbol = BINANCE_SYMBOL.lower()
        self.interval = interval or BINANCE_INTERVAL
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_{self.interval}"
        super().__init__(url, self._on_message)
        self._warning_printed = False

    def _on_message(self, ws: Any, message: str) -> None:
        try:
            data = json.loads(message)
            k = data.get("k")
            if not k or not k.get("x"):
                return
            candle_ts = k.get("t") // 1000
            now = int(datetime.now(tz=timezone.utc).timestamp())
            if now - candle_ts > 90:
                return
#             import global_state
            if global_state.last_candle_ts is not None and candle_ts <= global_state.last_candle_ts:
                return
            candle = {
                "timestamp": candle_ts,
                "open": float(k.get("o")),
                "high": float(k.get("h")),
                "low": float(k.get("l")),
                "close": float(k.get("c")),
                "volume": float(k.get("v")),
                "x": bool(k.get("x", False)),
                "source": "ws",
            }
            global_state.last_feed_time = time.time()
            if self.on_candle:
                self.on_candle(candle)
                global_state.last_candle_ts = candle_ts
        except Exception:
            if not self._warning_printed:
                self._warning_printed = True


# ---------------------------------------------------------------------------
# Entry logic facade
_MASTER: Optional[AndacEntryMaster] = None


def should_enter(candle: dict, indicator: dict, config: dict) -> AndacSignal:
    global _MASTER
    if _MASTER is None:
        _MASTER = AndacEntryMaster(
            lookback=config.get("lookback", SETTINGS.get("lookback", 20)),
            puffer=config.get("puffer", 10.0),
            vol_mult=config.get("volumen_factor", 1.2),
            opt_rsi_ema=config.get("opt_rsi_ema", False),
            opt_safe_mode=config.get("opt_safe_mode", False),
            opt_engulf=config.get("opt_engulf", False),
            opt_engulf_bruch=config.get("opt_engulf_bruch", False),
            opt_engulf_big=config.get("opt_engulf_big", False),
            opt_confirm_delay=config.get("opt_confirm_delay", False),
            opt_mtf_confirm=config.get("opt_mtf_confirm", False),
            opt_volumen_strong=config.get("opt_volumen_strong", False),
            opt_session_filter=config.get("opt_session_filter", False),
            cooldown=SETTINGS.get("cooldown", 0),
            max_drawdown_pct=SETTINGS.get("drawdown_pct", 0.0),
            max_loss=SETTINGS.get("max_loss", 0.0),
            sl_tp_manual_active=SETTINGS.get("sl_tp_manual_active", True),
        )
    else:
        _MASTER.lookback = config.get("lookback", _MASTER.lookback)
        _MASTER.puffer = config.get("puffer", _MASTER.puffer)
        _MASTER.vol_mult = config.get("volumen_factor", _MASTER.vol_mult)
        _MASTER.opt_rsi_ema = config.get("opt_rsi_ema", _MASTER.opt_rsi_ema)
        _MASTER.opt_safe_mode = config.get("opt_safe_mode", _MASTER.opt_safe_mode)
        _MASTER.opt_engulf = config.get("opt_engulf", _MASTER.opt_engulf)
        _MASTER.opt_engulf_bruch = config.get("opt_engulf_bruch", _MASTER.opt_engulf_bruch)
        _MASTER.opt_engulf_big = config.get("opt_engulf_big", _MASTER.opt_engulf_big)
        _MASTER.opt_confirm_delay = config.get("opt_confirm_delay", _MASTER.opt_confirm_delay)
        _MASTER.opt_mtf_confirm = config.get("opt_mtf_confirm", _MASTER.opt_mtf_confirm)
        _MASTER.opt_volumen_strong = config.get("opt_volumen_strong", _MASTER.opt_volumen_strong)
        _MASTER.opt_session_filter = config.get("opt_session_filter", _MASTER.opt_session_filter)
        _MASTER.cooldown = SETTINGS.get("cooldown", _MASTER.cooldown)
        _MASTER.max_drawdown_pct = SETTINGS.get("drawdown_pct", _MASTER.max_drawdown_pct)
        _MASTER.max_loss = SETTINGS.get("max_loss", _MASTER.max_loss)
        _MASTER.sl_tp_manual_active = SETTINGS.get("sl_tp_manual_active", _MASTER.sl_tp_manual_active)
    return _MASTER.evaluate(candle)


# ---------------------------------------------------------------------------
# Strategy filter helpers
_FILTER_CONFIG: Dict[str, Any] = {}


def set_filter_config(filters: Optional[Dict[str, Any]]) -> None:
    global _FILTER_CONFIG
    _FILTER_CONFIG = filters or {}


def get_filter_config() -> Dict[str, Any]:
    return _FILTER_CONFIG


# ---------------------------------------------------------------------------
# Main bot wrapper
class EntryMasterBot:
    """Central trading bot handling settings and execution."""

    def __init__(self) -> None:
        self.settings: Dict[str, Any] = SETTINGS.copy()

    def apply_settings(self, params: Optional[Dict[str, Any]] = None) -> None:
        if params:
            self.settings.update(params)

    def start(self, gui: Any | None = None) -> None:
#         from realtime_runner import run_bot_live
        run_bot_live(self.settings, gui)

    def start_simulation(self, gui: Any | None = None) -> None:
        self.apply_settings({"paper_mode": True})
        self.start(gui)

    def start_live(self, gui: Any | None = None) -> None:
        self.apply_settings({"paper_mode": False})
        self.start(gui)



# === from data_provider.py ===
# data_provider.py

# from __future__ import annotations

import logging
from typing import List, Optional, TypedDict
import time
import threading
import queue

# Import consolidated WebSocket implementation and settings
# from andac_entry_master import BinanceCandleWebSocket, BINANCE_SYMBOL, BINANCE_INTERVAL
from tkinter import Tk, StringVar
import requests
# from status_events import StatusDispatcher
# from config_manager import config

logger = logging.getLogger(__name__)

_CANDLE_WS_CLIENT: BinanceCandleWebSocket | None = None
_WS_CANDLES: list[Candle] = []
_CANDLE_LOCK = threading.Lock()
_CANDLE_QUEUE: queue.Queue[Candle] = queue.Queue(maxsize=100)
_PRELOAD_QUEUE_LIMIT = 2
_MAX_CANDLES = 1000
_CANDLE_WS_STARTED: bool = False
_FEED_MONITOR_THREAD: threading.Thread | None = None
_FEED_MONITOR_STARTED: bool = False
_FEED_CHECK_INTERVAL = 20
_TK_ROOT: Tk | None = None
price_var: StringVar | None = None
_DEFAULT_INTERVAL = BINANCE_INTERVAL
_LAST_CANDLE_TS: int | None = None


def _interval_to_seconds(interval: str) -> int:
    """Convert timeframe string like '1m' or '5h' to seconds."""
    try:
        if interval.endswith('m'):
            return int(interval[:-1]) * 60
        if interval.endswith('h'):
            return int(interval[:-1]) * 3600
        if interval.endswith('d'):
            return int(interval[:-1]) * 86400
    except Exception:
        pass
    return 60

class WebSocketStatus:
    running = False

    @classmethod
    def is_running(cls) -> bool:
        return cls.running

    @classmethod
    def set_running(cls, value: bool) -> None:
        cls.running = value

def init_price_var(master: Tk) -> None:
    global price_var, _TK_ROOT
    _TK_ROOT = master
    if price_var is None:
        price_var = StringVar(master=master, value="--")


def _fetch_rest_candles(interval: str, limit: int = 14) -> list["Candle"]:
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={BINANCE_SYMBOL}"
        f"&interval={interval}&limit={limit}"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    candles: list[Candle] = []
    for row in data:
        candles.append(
            {
                "timestamp": int(row[0] // 1000),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "x": True,
            }
        )
    return candles


def _load_initial_candles(interval: str, limit: int = 14, queue_limit: int = _PRELOAD_QUEUE_LIMIT) -> bool:
    StatusDispatcher.dispatch("feed", False, "REST-API-Call-14")
    try:
        candles = _fetch_rest_candles(interval, limit)
    except Exception as exc:
        logger.error("REST Candle Fetch failed: %s", exc)
        return False
    global _LAST_CANDLE_TS
    with _CANDLE_LOCK:
        _WS_CANDLES.extend(candles)
        if len(_WS_CANDLES) > _MAX_CANDLES:
            del _WS_CANDLES[:-_MAX_CANDLES]
        if candles:
            _LAST_CANDLE_TS = candles[-1]["timestamp"]
    for candle in candles[-queue_limit:]:
        candle["source"] = "preload"
        try:
            _CANDLE_QUEUE.put_nowait(candle)
        except queue.Full:
            pass
    return True

def start_candle_websocket(interval: str | None = None) -> None:
    global _CANDLE_WS_STARTED, _CANDLE_WS_CLIENT, _DEFAULT_INTERVAL

    if interval:
        _DEFAULT_INTERVAL = interval
    else:
        interval = _DEFAULT_INTERVAL

    if (
        _CANDLE_WS_STARTED
        and _CANDLE_WS_CLIENT
        and _CANDLE_WS_CLIENT.thread
        and _CANDLE_WS_CLIENT.thread.is_alive()
    ):
        logger.debug("Candle-WebSocket bereits aktiv")
        return
    if _CANDLE_WS_STARTED:
        stop_candle_websocket()
        logger.info("Candle-WebSocket neu gestartet")

    if not _load_initial_candles(interval, 14, _PRELOAD_QUEUE_LIMIT):
        raise RuntimeError("Initial candle download failed")

    logger.info("WebSocket Candle-Stream gestartet")
    _CANDLE_WS_CLIENT = BinanceCandleWebSocket(
        update_candle_feed,
        interval=interval,
    )
    _CANDLE_WS_CLIENT.start()
    _CANDLE_WS_STARTED = True

    start_time = time.time()
    error_logged = False
    while time.time() - start_time < 10:
        with _CANDLE_LOCK:
            has_candles = bool(_WS_CANDLES)
        if has_candles:
            logger.info("Erste Candle(s) empfangen – WebSocket läuft stabil")
            break
        if not error_logged and time.time() - start_time >= 5:
            logger.warning("FEED ERROR: Keine Candle-Daten empfangen nach 5s")
            error_logged = True
        time.sleep(0.5)
    else:
        logger.warning(
            "Kein Candle-Update nach 10s – prüfen, ob Binance-Daten verfügbar sind"
        )

    if not _FEED_MONITOR_STARTED:
        monitor_feed()

def stop_candle_websocket() -> None:
    global _CANDLE_WS_CLIENT, _CANDLE_WS_STARTED
    if _CANDLE_WS_CLIENT:
        try:
            _CANDLE_WS_CLIENT.stop()
        except Exception:
            pass
    _CANDLE_WS_CLIENT = None
    _CANDLE_WS_STARTED = False
    stop_feed_monitor()
    logger.info("Candle-WebSocket gestoppt")

_FEED_STUCK_COUNT = 0
_FEED_LAST_LEN = 0
_LAST_LEN_CHANGE_TS: float | None = None
_MONITOR_START_TS: float | None = None


def _monitor_loop() -> None:
    global _FEED_MONITOR_STARTED, _FEED_STUCK_COUNT, _FEED_LAST_LEN, _LAST_LEN_CHANGE_TS

    timeframe_sec = _interval_to_seconds(_DEFAULT_INTERVAL)
    start_ts = _MONITOR_START_TS or time.time()

    while _FEED_MONITOR_STARTED:
        time.sleep(_FEED_CHECK_INTERVAL)
        try:
#             import global_state

            last_ts = global_state.last_feed_time
            last_candle_time = get_last_candle_time()

            with _CANDLE_LOCK:
                current_len = len(_WS_CANDLES)

            if current_len != _FEED_LAST_LEN:
                _FEED_LAST_LEN = current_len

            last_update = _LAST_LEN_CHANGE_TS or start_ts
            if last_candle_time:
                last_update = max(last_update, last_candle_time)

            diff = time.time() - last_update

            if diff > timeframe_sec * 2:
                logger.warning(
                    "❌ Keine neue Candle seit %.0fs bei %s-Intervall – FEED ERROR",
                    diff,
                    _DEFAULT_INTERVAL,
                )
                _FEED_STUCK_COUNT += 1
                if _FEED_STUCK_COUNT >= 2:
                    stop_candle_websocket()
                    if not _CANDLE_WS_STARTED:
                        start_candle_websocket()
                    _FEED_STUCK_COUNT = 0
            else:
                logger.info("🕒 Letzte Candle vor %.0fs – alles OK", diff)
                _FEED_STUCK_COUNT = 0
        except Exception as exc:
            logger.error("Feed-Monitor Fehler: %s", exc)

def monitor_feed() -> None:
    global _FEED_MONITOR_STARTED, _FEED_MONITOR_THREAD, _MONITOR_START_TS, _FEED_LAST_LEN, _LAST_LEN_CHANGE_TS
    if _FEED_MONITOR_STARTED and _FEED_MONITOR_THREAD and _FEED_MONITOR_THREAD.is_alive():
        return

    logger.info("Candle-Feed Monitor gestartet")
    _FEED_MONITOR_STARTED = True
    _MONITOR_START_TS = time.time()
    with _CANDLE_LOCK:
        _FEED_LAST_LEN = len(_WS_CANDLES)
    _LAST_LEN_CHANGE_TS = None
    _FEED_MONITOR_THREAD = threading.Thread(
        target=_monitor_loop, daemon=True
    )
    _FEED_MONITOR_THREAD.start()

def stop_feed_monitor() -> None:
    global _FEED_MONITOR_STARTED, _FEED_MONITOR_THREAD
    if _FEED_MONITOR_STARTED:
        _FEED_MONITOR_STARTED = False
        if _FEED_MONITOR_THREAD and _FEED_MONITOR_THREAD.is_alive():
            _FEED_MONITOR_THREAD.join(timeout=1)
        _FEED_MONITOR_THREAD = None

def get_last_candle_time() -> Optional[float]:
    """Return timestamp of the latest received candle from the WebSocket."""
    try:
#         import global_state
        return global_state.last_candle_ts
    except Exception:
        return None



class Candle(TypedDict):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

def is_candle_valid(candle: dict) -> bool:
    required = ("timestamp", "close")
    return all(key in candle and candle[key] not in (None, "") for key in required)

def update_candle_feed(candle: Candle) -> None:
    logger.debug("update_candle_feed called: %s", candle)
    if not is_candle_valid(candle):
        logger.warning("Ungültige Candle empfangen: %s", candle)
        return

    global _LAST_LEN_CHANGE_TS, _FEED_LAST_LEN, _LAST_CANDLE_TS
    if _LAST_CANDLE_TS is not None and candle["timestamp"] <= _LAST_CANDLE_TS:
        logger.debug("Doppelte Candle ignoriert: %s", candle)
        return
    _LAST_CANDLE_TS = candle["timestamp"]
    candle["source"] = "ws"

    with _CANDLE_LOCK:
        _WS_CANDLES.append(candle)
        if len(_WS_CANDLES) > _MAX_CANDLES:
            _WS_CANDLES.pop(0)
        _FEED_LAST_LEN = len(_WS_CANDLES)
        _LAST_LEN_CHANGE_TS = time.time()
    try:
        _CANDLE_QUEUE.put_nowait(candle)
    except queue.Full:
        logger.warning("⚠️ Feed überlastet – Candles könnten verloren gehen")

    if price_var and _TK_ROOT:
        try:
            _TK_ROOT.after(0, lambda val=candle["close"]: price_var.set(str(val)))
        except Exception:
            pass

    WebSocketStatus.set_running(True)

def get_candle_queue() -> queue.Queue[Candle]:
    """Return the queue containing live candles."""
    return _CANDLE_QUEUE

def fetch_last_price() -> Optional[float]:
    candle = fetch_latest_candle()
    if candle:
        return candle.get("close")
    return None

def get_latest_candle_batch(limit: int = 100) -> List[Candle]:
    return get_live_candles(limit)

def get_live_candles(limit: int) -> List[Candle]:
    if not _CANDLE_WS_STARTED:
        start_candle_websocket()
    with _CANDLE_LOCK:
        return list(_WS_CANDLES[-limit:])

def fetch_latest_candle() -> Optional[Candle]:
    candles = get_latest_candle_batch(1)
    candle = candles[-1] if candles else None
    if candle and not is_candle_valid(candle):
        logger.warning("fetch_latest_candle: incomplete data %s", candle)
        return None
    return candle


# === from realtime_runner.py ===
# realtime_runner.py

import os
import time
import traceback
from datetime import datetime
import logging
import queue
import random
# import data_provider
from requests.exceptions import RequestException
from tkinter import messagebox

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def now_time() -> str:
    """Return the current time formatted as HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")

# from data_provider import (
#     fetch_latest_candle,
#     fetch_last_price,
#     get_last_candle_time,
#     get_live_candles,
#     start_candle_websocket,
#     get_candle_queue,
# )
# from andac_entry_master import (
#     BINANCE_INTERVAL,
#     BINANCE_SYMBOL,
#     open_position,
#     close_position,
#     close_partial_position as api_close_partial_position,
# )
# from status_block import print_entry_status
# from gui_bridge import GUIBridge
# from trading_gui_core import TradingGUI
# from trading_gui_logic import TradingGUILogicMixin
# from central_logger import log_triangle_signal
# from global_state import (
#     entry_time_global,
#     ema_trend_global,
#     atr_value_global,
#     position_global,
# )
# import global_state

# from andac_entry_master import (
#     calculate_ema,
#     calculate_atr,
#     macd_crossover_detected,
# )

# from andac_entry_master import AndacEntryMaster, AndacSignal
# from andac_entry_master import should_enter, AdaptiveSLManager
# from status_events import StatusDispatcher


# TIMEFILTER: GUI based time window check
def is_within_active_timeframe(gui) -> bool:
    if not gui.use_time_filter.get():
        return True
    now = datetime.now().time()
    for start_var, end_var in getattr(gui, "time_filters", []):
        try:
            start = datetime.strptime(start_var.get(), "%H:%M").time()
            end = datetime.strptime(end_var.get(), "%H:%M").time()
            if start <= now <= end:
                return True
        except ValueError:
            continue
    return False


def update_indicators(candles):
    atr = calculate_atr(candles, 14)
    closes = [c["close"] for c in candles if "close" in c]
    ema = calculate_ema(closes[-20:], 20)
    rsi = AndacEntryMaster._rsi(closes, 14)
    macd_cross = macd_crossover_detected(closes)
    return atr, ema, rsi, macd_cross


def handle_existing_position(position, candle, app, capital, live_trading,
                             last_printed_pnl, last_printed_price,
                             settings, now, signal=None, current_index=None):
    current = candle["close"]
    entry = position["entry"]
    pnl_live = calculate_futures_pnl(
        entry,
        current,
        position["leverage"],
        position["amount"],
        position["side"],
    )
    fee_live = position["amount"] * current * 0.00075
    pnl_live -= fee_live

    if (
        last_printed_pnl is None
        or last_printed_price is None
        or abs(pnl_live - last_printed_pnl) > 1.0
        or abs(current - last_printed_price) > 1.0
    ):
        logging.info(
            "⏳ Position offen (%s) | Entry: %.2f | Now: %.2f",
            position["side"],
            entry,
            current,
        )
        sl_val = position.get("sl")
        tp_val = position.get("tp")

        if isinstance(sl_val, (int, float)) and isinstance(tp_val, (int, float)):
            logging.info(
                "🎯 SL: %.2f | TP: %.2f | PnL: %.2f",
                sl_val,
                tp_val,
                pnl_live,
            )
        else:
            logging.warning(
                "🎯 SL/TP fehlen – SL: %s | TP: %s | PnL: %.2f",
                sl_val,
                tp_val,
                pnl_live,
            )
        last_printed_pnl = pnl_live
        last_printed_price = current

    app.update_live_trade_pnl(pnl_live)
    app.live_pnl = pnl_live

    tp_price = position.get("tp")
    partial_pct = settings.get("partial_close_pct", 0.5)
    partial_order_type = settings.get("partial_order_type", "market")

    if (
        settings.get("auto_partial_close", False)
        and tp_price is not None
        and not position.get("partial_closed", False)
    ):
        hit_tp = current >= tp_price if position["side"] == "long" else current <= tp_price
        if hit_tp:
            logging.info("💰 TP erreicht – Exit ausgelöst.")
            partial_volume = round(position.get("amount", 0) * partial_pct, 3)
            result = False
            if live_trading:
                try:
                    result = api_close_partial_position(partial_volume, partial_order_type)
                    if result is None:
                        logging.error("\u2757 Partial Close fehlgeschlagen – keine Position reduziert!")
                    if not result:
                        app.log_event("❗️Retry Partial Close...")
                        result = api_close_partial_position(partial_volume, partial_order_type)
                except Exception as e:
                    app.log_event(f"❌ Fehler beim Partial Close: {e}")
            else:
                result = True  # Simulation immer erfolgreich

            if result:
                _, realized = _basic_simulate_trade(
                    entry,
                    position["side"],
                    tp_price,
                    partial_volume,
                    position["leverage"],
                    FEE_MODEL,
                )
                old_cap = capital
                capital += realized
                check_plausibility(realized, old_cap, capital, partial_volume)
                position["amount"] -= partial_volume
                position["partial_closed"] = True
                app.log_event(
                    f"⚡ Auto Partial Close bei TP ausgelöst! ➖ {partial_volume} Kontrakte glattgestellt."
                )

    if (
        settings.get("simulate_partial", False)
        and tp_price is not None
        and position["amount"] > 0
    ):
        hit_tp_price = (
            current >= tp_price if position["side"] == "long" else current <= tp_price
        )
        if hit_tp_price:
            partial_amount = position["amount"] * settings.get("partial_pct", 0.5)
            logging.info(f"🔄 Simulierter Partial Close: {partial_amount} BTC")
            position["amount"] -= partial_amount

    if hasattr(app, "apc_enabled") and app.apc_enabled.get():
        try:
            apc_rate = float(app.apc_rate.get())
            apc_interval = int(app.apc_interval.get())
            apc_min_profit = float(app.apc_min_profit.get())
            if pnl_live > apc_min_profit and position["amount"] > 1:
                to_close = position["amount"] * (apc_rate / 100)
                if to_close < 1:
                    to_close = 1

                _, realized = _basic_simulate_trade(
                    entry,
                    position["side"],
                    current,
                    to_close,
                    position["leverage"],
                    FEE_MODEL,
                )
                old_cap = capital
                capital += realized
                check_plausibility(realized, old_cap, capital, to_close)
                position["amount"] -= to_close

                log_msg = (
                    f"⚡️ Teilverkauf {to_close:.2f} | Entry {entry:.2f} -> "
                    f"Exit {exit_price:.2f} | PnL {realized:.2f}$ | "
                    f"Balance {old_cap:.2f}->{capital:.2f} | Rest {position['amount']:.2f}"
                )
                app.log_event(log_msg)
                app.apc_status_label.config(text=log_msg, foreground="blue")
                if live_trading:
                    live_partial_close(position, capital, app, settings)
                if position["amount"] <= 0:
                    position = None
                    position_open = False
                    entry_time_global = None
                    app.log_event("✅ Position durch APC komplett geschlossen")
                    return position, capital, last_printed_pnl, last_printed_price, True
                time.sleep(apc_interval)
        except Exception as e:
            logging.error("Fehler bei Auto Partial Close: %s", e)

    tp_price = position.get("tp")
    sl_price = position.get("sl")
    if tp_price is None or sl_price is None:
        logging.warning("SL/TP Werte fehlen, überspringe Positionsprüfung")
        return position, capital, last_printed_pnl, last_printed_price, False

    high = candle.get("high", current)
    low = candle.get("low", current)

    hit_tp = False
    hit_sl = False
    exit_price = current

    if position["side"] == "long":
        if low <= sl_price:
            hit_sl = True
            exit_price = sl_price
            logging.info("\u26d4 SL erreicht – Exit ausgelöst.")
        elif high >= tp_price:
            hit_tp = True
            exit_price = tp_price
            logging.info("💰 TP erreicht – Exit ausgelöst.")
    else:
        if high >= sl_price:
            hit_sl = True
            exit_price = sl_price
            logging.info("\u26d4 SL erreicht – Exit ausgelöst.")
        elif low <= tp_price:
            hit_tp = True
            exit_price = tp_price
            logging.info("💰 TP erreicht – Exit ausgelöst.")

    timed_exit = False
    hold_duration = 0
    if (
        not live_trading
        and current_index is not None
        and position.get("entry_index") is not None
    ):
        hold_duration = current_index - position["entry_index"]
        if hold_duration >= MAX_HOLD_CANDLES:
            timed_exit = True

    if hasattr(app, "current_position") and app.current_position:
        app.current_position["bars_open"] = hold_duration
        if hasattr(app, "update_trade_display"):
            app.update_trade_display()

    opp_exit = False
    if app:
        try:
            if hasattr(app, "update_filter_params"):
                app.update_filter_params()
            else:
                logging.debug("🔁 update_filter_params() nicht verfügbar – übersprungen.")
        except Exception as e:
            logging.warning(f"⚠️ update_filter_params() fehlgeschlagen: {e}")
    if signal and signal in ("long", "short"):
        opp_exit = (
            (position["side"] == "long" and signal == "short") or
            (position["side"] == "short" and signal == "long")
        )
        if opp_exit:
            logging.info(
                f"📉 Gegensignal erkannt ({signal}) – Exit ausgelöst."
            )

    should_close = hit_tp or hit_sl or timed_exit or opp_exit

    if should_close:
        new_capital = simulate_trade(
            position,
            exit_price,
            current_index if current_index is not None else 0,
            settings,
            capital,
        )
        pnl = new_capital - capital
        old_cap = capital
        capital = new_capital
        check_plausibility(pnl, old_cap, capital, position["amount"])


        app.update_pnl(pnl)
        app.update_capital(capital)
        app.update_last_trade(position["side"], entry, exit_price, pnl)
        if hasattr(app, "current_position"):
            app.current_position = None
            if hasattr(app, "update_trade_display"):
                app.update_trade_display()

        if hit_tp:
            reason = "TP erreicht"
        elif hit_sl:
            reason = "SL erreicht"
        elif timed_exit:
            reason = (
                f"\u23F1 Timed Exit: {position['side'].upper()} @ {exit_price:.2f} "
                f"nach {hold_duration} Kerzen"
            )
        else:
            reason = "Gegensignal"

        if timed_exit:
            stamp = now_time()
            log_msg = f"[{stamp}] {reason}"
            logger.info(log_msg)
            logger.info(
                f"💸 Simuliertes Kapital: ${capital:.2f} | Realisierter PnL: {pnl:.2f}"
            )
        elif opp_exit:
            stamp = datetime.now().strftime("%H:%M:%S")
            log_msg = f"[{stamp}] {reason} bei {exit_price:.2f} | PnL {pnl:.2f}"
        else:
            log_msg = (
                f"\U0001F4A5 Position geschlossen ({position['side']}) | Entry {entry:.2f} -> Exit {exit_price:.2f} | PnL {pnl:.2f}"
            )
        logging.info(log_msg)
        app.log_event(log_msg)
        if live_trading:
            close_position()

        app.update_live_trade_pnl(0.0)
        app.live_pnl = 0.0

        position = None
        position_open = False
        last_exit_time = now
        entry_time_global = None
        return position, capital, last_printed_pnl, last_printed_price, True

    return position, capital, last_printed_pnl, last_printed_price, False

# from console_status import (
#     print_start_banner,
#     print_stop_banner,
#     print_warning,
#     print_info,
# )
# from pnl_utils import calculate_futures_pnl, check_plausibility
# from simulator import FeeModel, simulate_trade as _basic_simulate_trade

# Maximum number of candles to keep a simulated trade open
MAX_HOLD_CANDLES = 10
FEE_MODEL = FeeModel(taker_fee=0.0004)
POSITION_SIZE = 0.2

gui_bridge = None

def live_partial_close(position, capital, app, settings):
    partial_pct = settings.get("partial_pct", 0.5)
    partial_amount = position["amount"] * partial_pct
    result = api_close_partial_position(
        partial_amount,
        settings.get("partial_order_type", "market"),
    )
    if result:
        if hasattr(app, "send_status_to_gui"):
            app.send_status_to_gui("partial_closed", result)
    else:
        logging.error("❗ Auto Partial Close fehlgeschlagen.")

def set_gui_bridge(gui_instance):
    global gui_bridge
    gui_bridge = GUIBridge(gui_instance)

def cancel_trade(position, app):
    print(f"❌ Abbruch der Position: {position['side']} @ {position['entry']:.2f}")
    app.position = None
    if hasattr(app, "current_position"):
        app.current_position = None
        if hasattr(app, "update_trade_display"):
            app.update_trade_display()
    app.log_event("🛑 Position wurde durch Benutzer abgebrochen!")
    return None

def emergency_exit_position(app):
    if app.position:
        print("❗️ Notausstieg ausgelöst! Die Position wird geschlossen.")
        cancel_trade(app.position, app)
        app.log_event("🛑 Position wurde im Notausstiegsmodus geschlossen!")
    else:
        print("❌ Keine Position offen, um sie zu schließen!")
        app.log_event(
            "❌ Keine offene Position zum Notausstiegsmodus gefunden."
        )


def wait_for_initial_candles(
    app: TradingGUILogicMixin | TradingGUI | None = None,
    required: int = 14,
    timeout: int = 20,
) -> list[dict]:

    start_time = time.time()
    last_logged = -1

    while True:
        candles = get_live_candles(required)
        count = len(candles)
        if count >= required:
            msg = "✅ ATR bereit – Starte Bot-Logik."
            logging.info(msg)
            if app and hasattr(app, "update_status"):
                app.update_status(msg)
            else:
                gui_bridge.update_status(msg)
            return candles

        elapsed = time.time() - start_time
        if elapsed >= timeout:
            msg = (
                f"⚠️ Timeout beim Warten auf Candles – starte trotzdem ({count}/{required})"
            )
            logging.warning(msg)
            if app and hasattr(app, "update_status"):
                app.update_status(msg)
            else:
                gui_bridge.update_status(msg)
            return candles

        if count != last_logged:
            progress = (
                f"⏳ Warte auf ATR-Berechnung... ({count}/{required} Candles erhalten)"
            )
            logging.info(progress)
            if app and hasattr(app, "update_status"):
                app.update_status(progress)
            else:
                gui_bridge.update_status(progress)
            last_logged = count
        time.sleep(1)

def _run_bot_live_inner(settings=None, app=None):
    global entry_time_global, position_global, ema_trend_global, atr_value_global

    if app:
        set_gui_bridge(app)
    else:
        set_gui_bridge(None)

    capital = float(gui_bridge.capital) if gui_bridge else settings.get(
        "capital", 2000
    )
    start_capital = capital

    print_start_banner(capital)

    interval_setting = settings.get("interval", BINANCE_INTERVAL)

    if "track_history" not in settings:
        settings["track_history"] = True
        settings["trade_history"] = []

    if app:
        settings["log_event"] = app.log_event
        start_capital = capital
        if hasattr(app, "sl_tp_status_var"):
            app.sl_tp_status_var.set("")
    

    multiplier = gui_bridge.multiplier
    capital = float(gui_bridge.capital)
    start_capital = capital
    interval = interval_setting
    auto_multi = gui_bridge.auto_multiplier
    leverage = multiplier
    live_requested = gui_bridge.live_trading
    paper_mode = settings.get("paper_mode", True)
    live_trading = live_requested and not paper_mode
    settings["paper_mode"] = not live_trading

    # REMOVED: SessionFilter

    config = {
        "lookback": int(app.andac_lookback.get()),
        "puffer": float(app.andac_puffer.get()),
        "volumen_factor": float(app.andac_vol_mult.get()),
        "opt_rsi_ema": app.andac_opt_rsi_ema.get(),
        "opt_safe_mode": app.andac_opt_safe_mode.get(),
        "opt_engulf": app.andac_opt_engulf.get(),
        "opt_engulf_bruch": app.andac_opt_engulf_bruch.get(),
        "opt_engulf_big": app.andac_opt_engulf_big.get(),
        "opt_confirm_delay": app.andac_opt_confirm_delay.get(),
        "opt_mtf_confirm": app.andac_opt_mtf_confirm.get(),
        "opt_volumen_strong": app.andac_opt_volumen_strong.get(),
        "opt_session_filter": app.andac_opt_session_filter.get(),
    }
#     from andac_entry_master import get_filter_config
    filters = get_filter_config()
    cooldown_after_exit = filters.get("cooldown_after_exit", settings.get("cooldown_after_exit", 120))
    sl_tp_mode = filters.get("sl_mode", settings.get("sl_tp_mode", "adaptive"))
    max_trades_hour = settings.get("max_trades_hour", 5)
    fee_percent = settings.get("fee_percent", 0.075)
    require_closed_candles = filters.get("require_closed_candles", True)
    FEE_MODEL.taker_fee = fee_percent / 100

    last_exit_time = 0.0
    trade_times: list[float] = []
    adaptive_sl = AdaptiveSLManager()

    candles = []
    position = None
    position_entry_index = None
    entry_price = None
    position_open = False
    current_position_direction = None
    last_printed_price = None

    last_printed_pnl = None
    last_printed_price = None

    no_signal_printed = False
    first_feed = False
    candle_warning_printed = False
    previous_signal = None

    def process_candle(candle: dict) -> None:
        nonlocal candles, position, capital, last_printed_pnl, last_printed_price, \
                 no_signal_printed, first_feed, previous_signal, position_entry_index, \
                 entry_price, position_open, current_position_direction, last_exit_time
        if not first_feed:
            first_feed = True
            if hasattr(app, "log_event"):
                app.log_event("✅ Erster Marktdaten-Feed empfangen")
        candles.append(candle)
        if len(candles) > 100:
            candles.pop(0)

        atr_value, ema, rsi_val, macd_cross = update_indicators(candles)
        atr_value_global = atr_value
        settings["ema_value"] = ema

        if ema is not None:
            ema_trend_global = "⬆️" if candle["close"] > ema else "⬇️"
        else:
            ema_trend_global = "❓"

        close_price = candle["close"]
        now = time.time()

        current_index = len(candles) - 1
        if position:
            current_price = fetch_last_price()
            if (
                (position["side"] == "long" and current_price >= position["tp"]) or
                (position["side"] == "short" and current_price <= position["tp"]) or
                (position["side"] == "long" and current_price <= position["sl"]) or
                (position["side"] == "short" and current_price >= position["sl"])
            ):
                capital = simulate_trade(position, current_price, current_index, settings, capital)
                position = None
                position_open = False

        if not is_within_active_timeframe(app):
            logger.info("⏳ Außerhalb der Handelszeit – kein Entry erlaubt")
            time.sleep(1)
            return

        if hasattr(app, "auto_apply_recommendations") and app.auto_apply_recommendations.get():
            try:
                app.apply_recommendations()
            except Exception as e:
                logging.error("Auto recommendation failed: %s", e)

        lookback = config.get("lookback", 20)
        recent = candles[-(lookback + 1):]
        highs = [c["high"] for c in recent[:-1]]
        lows = [c["low"] for c in recent[:-1]]
        vols = [c.get("volume", 0.0) for c in recent[:-1]]
        avg_volume = sum(vols) / len(vols) if vols else candle.get("volume", 0.0)
        high_lb = max(highs) if highs else candle["high"]
        low_lb = min(lows) if lows else candle["low"]
        prev_close = recent[-2]["close"] if len(recent) > 1 else None
        prev_open = recent[-2]["open"] if len(recent) > 1 else None

        if require_closed_candles and not candle.get("x", True):
            logging.info("🕒 Candle noch nicht geschlossen – Signal verworfen.")
            return


        indicator = {
            "rsi": rsi_val,
            "atr": atr_value,
            "avg_volume": avg_volume,
            "high_lookback": high_lb,
            "low_lookback": low_lb,
            "prev_close": prev_close,
            "prev_open": prev_open,
            "mtf_ok": True,
            "prev_bull_signal": previous_signal == "long",
            "prev_baer_signal": previous_signal == "short",
        }

        andac_signal: AndacSignal = should_enter(candle, indicator, config)
        entry_type = andac_signal.signal
        previous_signal = entry_type
        stamp = datetime.now().strftime("%H:%M:%S")
        if entry_type:
            triangle_msg = log_triangle_signal(entry_type, close_price)
            if hasattr(app, "log_event"):
                app.log_event(triangle_msg)
            msg = f"[{stamp}] Signal erkannt: {entry_type.upper()} ({BINANCE_SYMBOL} @ {close_price:.2f})"
            logging.info(msg)
            if hasattr(app, "log_event"):
                app.log_event(msg)
        if entry_type and not live_trading and position is None:
            entry_price = fetch_last_price()
            amount = capital / entry_price
            position = {
                "entry": entry_price,
                "amount": amount,
                "side": entry_type,
                "leverage": settings.get("leverage", 1),
                "tp": entry_price * (1 + 0.01) if entry_type == "long" else entry_price * (1 - 0.01),
                "sl": entry_price * (1 - 0.005) if entry_type == "long" else entry_price * (1 + 0.005),
                "entry_index": len(candles) - 1,
            }
            logging.info(f"🧪 Simulierter Entry: {entry_type.upper()} @ {entry_price:.2f}")
            position_open = True
            position_entry_index = len(candles) - 1
        elif andac_signal.reasons:
            reason_msg = ", ".join(andac_signal.reasons)
            msg = f"[{stamp}] Signal verworfen: {reason_msg}"
            logging.info(msg)
            if hasattr(app, "log_event"):
                app.log_event(msg)
            if hasattr(app, "last_reason_var") and andac_signal.reasons:
                app.last_reason_var.set(f"Verworfen wegen: {andac_signal.reasons[-1]}")

        # Timed Exit Logic for simulation mode
        if not live_trading and position_open:
            hold_duration = len(candles) - 1 - position_entry_index
            if hold_duration >= MAX_HOLD_CANDLES:
                exit_price = candle["close"]
                direction = current_position_direction
                new_capital = simulate_trade(
                    position,
                    exit_price,
                    len(candles) - 1,
                    settings,
                    capital,
                )
                pnl = new_capital - capital
                capital = new_capital
                app.update_pnl(pnl)
                app.update_capital(capital)
                app.update_last_trade(direction.lower(), entry_price, exit_price, pnl)
                if hasattr(app, "current_position"):
                    app.current_position = None
                    if hasattr(app, "update_trade_display"):
                        app.update_trade_display()
                position_open = False
                position = None
                app.position = None
                position_global = None
                entry_time_global = None
                logger.info(
                    f"[{now_time()}] \u23F1 Timed Exit: {direction} @ {exit_price:.2f} nach {hold_duration} Kerzen"
                )
                logger.info(
                    f"💸 Simuliertes Kapital: ${capital:.2f} | Realisierter PnL: {pnl:.2f}"
                )
                return

        if position:
            position_data = handle_existing_position(
                position,
                candle,
                app,
                capital,
                live_trading,
                last_printed_pnl,
                last_printed_price,
                settings,
                now,
                entry_type,
                len(candles) - 1,
            )
            position, capital, last_printed_pnl, last_printed_price, closed = position_data
            if closed:
                return
            no_signal_printed = False
            return

        if not position:
            if entry_type:
                no_signal_printed = False
                if now - last_exit_time < cooldown_after_exit:
                    logging.info("⏳ Cooldown aktiv – kein neuer Entry")
                    return
                trade_times[:] = [t for t in trade_times if now - t < 3600]
                if len(trade_times) >= max_trades_hour:
                    logging.info("⏸ Entry-Limit erreicht – kein neuer Trade")
                    return
                entry = candle["close"]
                slip = random.uniform(*FEE_MODEL.slippage_range)
                entry_exec = entry * (1 + slip) if entry_type == "long" else entry * (1 - slip)
                amount = capital * POSITION_SIZE
                sl = tp = None

                if sl_tp_mode == "manual":
                    sl = gui_bridge.manual_sl
                    tp = gui_bridge.manual_tp
                else:
                    try:
                        sl, tp = adaptive_sl.get_adaptive_sl_tp(entry_type, entry, candles)
                    except Exception as e:
                        logging.error("Adaptive SL Fehler: %s", e)
                        sl = tp = None

                if sl is None or tp is None:
                    return

                spread_buffer = entry * (fee_percent / 100)
                if entry_type == "long":
                    sl -= spread_buffer
                    tp += spread_buffer
                else:
                    sl += spread_buffer
                    tp -= spread_buffer



                position = {
                    "side": entry_type,
                    "entry": entry_exec,
                    "entry_time": now,
                    "entry_index": len(candles) - 1,
                    "sl": sl,
                    "tp": tp,
                    "amount": amount,
                    "initial_amount": amount,
                    "leverage": leverage,
                }

                entry_fee = amount * leverage * FEE_MODEL.taker_fee
                if entry_fee > 0:
                    capital -= entry_fee
                    app.log_event(f"💸 Entry Fee {entry_fee:.2f}$")

                position_global = position
                entry_time_global = now
                app.position = position
                app.current_position = {
                    "direction": entry_type.upper(),
                    "entry_price": entry_exec,
                    "entry_time": datetime.now(),
                    "bars_open": 0,
                }
                position_entry_index = len(candles) - 1
                entry_price = candle["close"]
                tp_val = settings.get("manual_tp", None)
                sl_val = settings.get("manual_sl", None)
                if tp_val is not None:
                    position["tp"] = (
                        entry_price * (1 + tp_val / 100)
                        if entry_type == "long"
                        else entry_price * (1 - tp_val / 100)
                    )
                if sl_val is not None:
                    position["sl"] = (
                        entry_price * (1 - sl_val / 100)
                        if entry_type == "long"
                        else entry_price * (1 + sl_val / 100)
                    )
                if tp_val is not None or sl_val is not None:
                    app.log_event(
                        f"🎯 Manuelles TP/SL gesetzt → TP: {position.get('tp', '–')} | SL: {position.get('sl', '–')}"
                    )
                position_open = True
                current_position_direction = entry_type.upper()
                trade_times.append(now)

                msg = f"[{stamp}] Trade platziert: {entry_type.upper()} ({entry_exec:.2f})"
                logging.info(msg)
                if hasattr(app, "log_event"):
                    app.log_event(msg)
                if hasattr(app, "update_trade_display"):
                    app.update_trade_display()

                if amount > 0 and live_trading:
                    try:
                        direction = "BUY" if entry_type == "long" else "SELL"
                        res = open_position(direction, amount)
                        if res is None:
                            raise RuntimeError("Order placement failed")
                        if hasattr(app, "send_status_to_gui"):
                            app.send_status_to_gui("entry_opened", position)
                    except Exception as e:
                        logging.error("Orderplatzierung fehlgeschlagen: %s", e)
            else:
                if not no_signal_printed:
                    logging.info("➖ Ich warte auf ein Indikator Signal")
                    no_signal_printed = True

    candle_queue = get_candle_queue()

    if not data_provider._CANDLE_WS_STARTED:
        start_candle_websocket(interval_setting)
    else:
        logging.info("Candle WebSocket already running")

    preload = candle_queue.qsize()
    if preload:
        flush_limit = min(preload, 2)
        logging.info("\U0001F504 Clean Flush %s Candles", flush_limit)
        for _ in range(flush_limit):
            try:
                process_candle(candle_queue.get_nowait())
            except queue.Empty:
                break

    logging.info(
        "Candle queue initialisiert (%s Candles im Buffer)", candle_queue.qsize()
    )

    ATR_REQUIRED = 14
    candles_ready = wait_for_initial_candles(app, ATR_REQUIRED)
    atr_tmp = calculate_atr(candles_ready, ATR_REQUIRED)
    atr_value_global = atr_tmp
    if app and hasattr(app, "update_status"):
        app.update_status("✅ Bereit")
    else:
        gui_bridge.update_status("✅ Bereit")

    while capital > 0 and not getattr(app, "force_exit", False):
        if getattr(app, "should_stop", False):
            logging.info("\U0001F6D1 Bot-Stop erkannt – beende Live-Modus.")
            if hasattr(app, "send_status_to_gui"):
                app.send_status_to_gui("status", "stopped")
            return
        if not getattr(app, "running", False):
            time.sleep(1)
            continue
        if not getattr(app, "feed_ok", True):
            print(
                f"🧪 Letzter Feed-Eingang vor {time.time() - global_state.last_feed_time:.1f} Sekunden"
            )
            time.sleep(1)
            continue
        # Verarbeite alle verfügbaren Candles aus der Queue
        while True:
            try:
                process_candle(candle_queue.get_nowait())
            except queue.Empty:
                break

        backlog = candle_queue.qsize()
        if backlog > 5:
            if not candle_warning_printed:
                logging.warning("⚠️ Candle-Backlog > %s – mögliche Latenz!", backlog)
                StatusDispatcher.dispatch("feed", False, "Candle-Lag")
                candle_warning_printed = True
        else:
            if backlog == 0:
                StatusDispatcher.dispatch("feed", True)
            candle_warning_printed = False
        time.sleep(0.1)

    reason = "Kapital aufgebraucht" if capital <= 0 else "Loop beendet"
    print_stop_banner(reason)

def run_bot_live(settings=None, app=None):
    """Wrapper for _run_bot_live_inner with error handling."""
    try:
        _run_bot_live_inner(settings, app)
    except RequestException:
        if app:
            messagebox.showerror(
                "Startfehler",
                "❌ API-Zugang ungültig oder Server nicht erreichbar.",
            )
        logging.error("API error during bot start", exc_info=True)
    except (KeyError, ValueError) as exc:
        if app:
            messagebox.showerror("Startfehler", f"❌ Konfigurationsfehler: {exc}")
        logging.error("Configuration error during bot start", exc_info=True)
    except Exception as exc:
        if app:
            messagebox.showerror("Startfehler", f"❌ Botstart fehlgeschlagen: {exc}")
        logging.error("Unexpected error during bot start", exc_info=True)


def simulate_trade(position: dict, exit_price: float, candle_index: int,
                   settings: dict, capital: float) -> float:
    """Simulate a trade outcome and update capital/history."""

    fee_rate = FEE_MODEL.taker_fee
    entry = position["entry"]
    qty = position["amount"]
    side = position["side"]
    leverage = position.get("leverage", 1)

    max_qty = (capital * leverage) / entry if entry else qty
    if qty > max_qty:
        logging.warning(
            "⚠️ Kontraktgröße reduziert: %.2f -> %.2f", qty, max_qty
        )
        qty = max_qty

    pnl = (exit_price - entry) if side == "long" else (entry - exit_price)
    pnl_value = pnl * qty * leverage

    fees = (entry + exit_price) * qty * fee_rate
    net_result = pnl_value - fees
    net_result = max(-capital, net_result)

    base = capital
    if base <= 0:
        logging.warning("⚠️ Kapital <= 0 – PnL-Berechnung kann ungenau werden")
        base = 1

    percent_change = (net_result / base) * 100

    direction = "LONG" if side == "long" else "SHORT"
    logging.info(
        f"[{time.strftime('%H:%M:%S')}] \U0001F4B0 Trade abgeschlossen: {direction} {entry:.2f} → {exit_price:.2f} | PnL: {net_result:.2f}$ ({percent_change:.2f}%)"
    )

    if settings.get("track_history"):
        settings.setdefault("trade_history", [])
        settings["trade_history"].append(
            {
                "time": time.strftime("%H:%M:%S"),
                "entry": entry,
                "exit": exit_price,
                "side": direction,
                "pnl": round(net_result, 2),
                "percent": round(percent_change, 2),
                "bars_open": candle_index - position.get("entry_index", 0),
            }
        )

    return capital + net_result


# === from main.py ===
# main.py

import os
import json
import threading
import time
from datetime import datetime

import tkinter as tk
from colorama import Fore, Style, init
# from central_logger import setup_logging

# Bot wrapper from andac_entry_master
# from andac_entry_master import EntryMasterBot
# from config_manager import config
# from system_monitor import SystemMonitor
# from trading_gui_core import TradingGUI
# from trading_gui_logic import TradingGUILogicMixin
# from api_key_manager import APICredentialManager
# from gui_bridge import GUIBridge
from tkinter import messagebox
from requests.exceptions import RequestException
# from global_state import entry_time_global, ema_trend_global, atr_value_global
# import data_provider

root = tk.Tk()
data_provider.init_price_var(root)
price_var = data_provider.price_var

init(autoreset=True)
setup_logging()
bot = EntryMasterBot()

class EntryMasterGUI(TradingGUI, TradingGUILogicMixin):
    pass

def load_settings_from_file(filename="tuning_config.json"):
    """Load settings into the central config manager."""
    if not os.path.exists(filename):
        return
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        bot.apply_settings(data)
        config.load_json(filename)
    except Exception as e:
        print(f"⚠️ Konnte {filename} nicht laden: {e}")

def safe_run_bot(gui):
    """Start EntryMasterBot with GUI-friendly error handling."""
    try:
        bot.start(gui)
    except RequestException:
        messagebox.showerror(
            "Startfehler",
            "❌ API-Zugang ungültig oder Server nicht erreichbar.",
        )
        gui.running = False
    except (KeyError, ValueError) as exc:
        messagebox.showerror("Startfehler", f"❌ Konfigurationsfehler: {exc}")
        gui.running = False
    except Exception as exc:
        messagebox.showerror("Startfehler", f"❌ Botstart fehlgeschlagen: {exc}")
        gui.running = False

def bot_control(gui):
    while True:
        cmd = input("💻 CMD> ").strip().lower()
        if cmd == "start":
            if not gui.running:
                load_settings_from_file()
                bot.apply_settings({"paper_mode": not gui.live_trading.get()})
                mode_text = "LIVE-MODUS" if gui.live_trading.get() else "SIMULATIONS-MODUS"
                print(f"🚀 Bot gestartet: {mode_text}")
                gui.running = True
                threading.Thread(target=safe_run_bot, args=(gui,), daemon=True).start()
            else:
                print("⚠️ Bot läuft bereits")
        elif cmd == "stop":
            gui.force_exit = True
            print("⛔ Trade-Abbruch gesendet")
        elif cmd == "status":
            try:
                pnl = round(getattr(gui, "live_pnl", 0.0), 1)
                farbe = (
                    Fore.GREEN + "🟢" if pnl > 0 else
                    Fore.RED + "🔴" if pnl < 0 else
                    Fore.YELLOW + "➖"
                )
                laufzeit = int(time.time() - entry_time_global) if entry_time_global else 0
                uhrzeit = datetime.now().strftime("%H:%M:%S")
                datum = datetime.now().strftime("%d.%m.%Y")
                capital = 0.0
                if hasattr(gui, "capital_var"):
                    try:
                        capital = float(gui.capital_var.get())
                    except Exception:
                        pass
                leverage = bot.settings.get("leverage", 20)
                if hasattr(gui, "multiplier_var") and hasattr(gui.multiplier_var, "get"):
                    try:
                        leverage = float(gui.multiplier_var.get())
                    except Exception:
                        pass
                trade_info = "--- (wartet)"
                if hasattr(gui, "position") and gui.position:
                    trade_info = f"{gui.position['side'].upper()} @ {gui.position['entry']}"
                filter_status = {
                    "RSI/EMA": gui.andac_opt_rsi_ema.get(),
                    "SAFE": gui.andac_opt_safe_mode.get(),
                    "ENG": gui.andac_opt_engulf.get(),
                    "BRUCH": gui.andac_opt_engulf_bruch.get(),
                    "BIG": gui.andac_opt_engulf_big.get(),
                    "DELAY": gui.andac_opt_confirm_delay.get(),
                    "MTF": gui.andac_opt_mtf_confirm.get(),
                    "VOL": gui.andac_opt_volumen_strong.get(),
                }
                filter_line = "🎛 Andac: " + " ".join(
                    f"{k}{'✅' if v else '❌'}" for k, v in filter_status.items()
                )
                status = (
                    f"{farbe} Aktueller PnL: ${pnl:.1f} | Laufzeit: {laufzeit}s | ⏰ {uhrzeit} | 📅 {datum}\n"
                    f"💼 Kapital: ${capital:.2f} | 📊 Lev: x{leverage} | 📍 Trade: {trade_info}\n"
                    f"📉 ATR: ${atr_value_global if atr_value_global is not None else 0.0:.1f} | 📈 EMA: {ema_trend_global} | 🚀 Modus: {'LIVE' if gui.live_trading.get() else 'SIMULATION'}\n"
                    f"{filter_line}"
                )
                print(status + Style.RESET_ALL)
            except Exception as e:
                print(f"❌ Fehler bei 'status': {e}")
        elif cmd == "restart":
#             from global_state import reset_global_state
            gui.force_exit = True
            reset_global_state()
            print("♻️ Bot zurückgesetzt")
        else:
            print("❓ Unbekannter Befehl. Verfügbar: start / stop / status / restart")

def on_gui_start(gui):
    if gui.running:
        print("⚠️ Bot läuft bereits (GUI-Schutz)")
        return
    load_settings_from_file()
    bot.apply_settings({
        "interval": gui.interval.get(),
        "paper_mode": not gui.live_trading.get(),
    })
    mode_text = "LIVE-MODUS" if gui.live_trading.get() else "SIMULATIONS-MODUS"
    print(f"🚀 Bot gestartet: {mode_text}")
    gui.running = True
    threading.Thread(target=safe_run_bot, args=(gui,), daemon=True).start()

def main():
    load_settings_from_file()
    config.load_env()

    # Candle WebSocket will start automatically when needed
    cred_manager = APICredentialManager()
    gui = EntryMasterGUI(root, cred_manager=cred_manager)
    gui_bridge = GUIBridge(gui_instance=gui, bot=bot)
    gui.callback = lambda: on_gui_start(gui)

    gui.system_monitor = SystemMonitor(gui)
    gui.system_monitor.start()

    threading.Thread(target=bot_control, args=(gui,), daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()



# === from test_api_key_manager.py ===
# test_api_key_manager.py
import os
import unittest
# from api_key_manager import APICredentialManager

class CredentialManagerTest(unittest.TestCase):
    def test_set_and_clear(self):
        mgr = APICredentialManager()
        mgr.set_credentials('k', 's')
        self.assertEqual(mgr.get_key(), 'k')
        self.assertEqual(mgr.get_secret(), 's')
        mgr.clear()
        self.assertIsNone(mgr.get_key())
        self.assertIsNone(mgr.get_secret())

    def test_load_from_env(self):
        os.environ["BITMEX_API_KEY"] = "env_key"
        os.environ["BITMEX_API_SECRET"] = "env_secret"
        mgr = APICredentialManager()
        loaded = mgr.load_from_env()
        self.assertTrue(loaded)
        self.assertEqual(mgr.get_key(), "env_key")
        self.assertEqual(mgr.get_secret(), "env_secret")
        mgr.clear()
        del os.environ["BITMEX_API_KEY"]
        del os.environ["BITMEX_API_SECRET"]

# if __name__ == '__main__':
#     unittest.main()


# === from test_entry_logic.py ===
import unittest
# from andac_entry_master import should_enter, _MASTER

class EntryLogicTest(unittest.TestCase):
    def test_entry_signal_rsi_engulfing(self):
        global _MASTER
        _MASTER = None
        config = {
            "lookback": 1,
            "puffer": 1,
            "volumen_factor": 1.2,
            "opt_engulf": True,
        }

        filler = {"open":100, "high":100, "low":99, "close":100, "volume":1000}
        prev = {"open":108, "high":110, "low":90, "close":102, "volume":1000}
        should_enter(filler, {}, config)
        should_enter(prev, {}, config)
        candle = {"open":100, "high":112, "low":98, "close":110, "volume":2000}
        signal = should_enter(candle, {}, config)
        self.assertEqual(signal.signal, "long")

# if __name__ == '__main__':
#     unittest.main()


# === from test_feed_parser.py ===
import unittest
import json
from datetime import datetime, timezone

# from andac_entry_master import BinanceCandleWebSocket

class FeedParserTest(unittest.TestCase):
    def test_parse_ws_candle(self):
        ws = BinanceCandleWebSocket()
        result = []
        def _collect(c):
            result.append(c)
        ws.on_candle = _collect
        ts = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        msg = json.dumps({
            "k": {
                "t": ts,
                "x": True,
                "o": "10",
                "h": "12",
                "l": "9",
                "c": "11",
                "v": "100"
            }
        })
        ws._on_message(None, msg)
        self.assertEqual(len(result), 1)
        candle = result[0]
        self.assertEqual(candle["open"], 10.0)
        self.assertEqual(candle["close"], 11.0)
        self.assertEqual(candle["high"], 12.0)
        self.assertEqual(candle["low"], 9.0)
        self.assertEqual(candle["volume"], 100.0)

    def test_ws_deduplication(self):
#         import global_state
        global_state.reset_global_state()
        ws = BinanceCandleWebSocket()
        collected = []
        ws.on_candle = collected.append
        ts = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        msg = json.dumps({
            "k": {
                "t": ts,
                "x": True,
                "o": "1",
                "h": "1",
                "l": "1",
                "c": "1",
                "v": "1",
            }
        })
        ws._on_message(None, msg)
        ws._on_message(None, msg)  # duplicate
        self.assertEqual(len(collected), 1)

# if __name__ == '__main__':
#     unittest.main()


# === from test_pnl_utils.py ===
# test_pnl_utils.py
import unittest
# from pnl_utils import calculate_futures_pnl

class PnlUtilsTest(unittest.TestCase):
    def test_example(self):
        pnl = calculate_futures_pnl(100, 100.2, leverage=20, amount=1000, side='long')
        self.assertAlmostEqual(pnl, 40.0, places=2)

# if __name__ == '__main__':
#     unittest.main()


# === from test_sl_tp_logic.py ===
import unittest
# from andac_entry_master import AdaptiveSLManager

class SLTPLogicTest(unittest.TestCase):
    def test_adaptive_sl_tp_long(self):
        manager = AdaptiveSLManager()
        candles = [
            {"high": 105, "low": 95, "close": 100},
        ] * 15
        sl, tp = manager.get_adaptive_sl_tp("long", 100, candles)
        self.assertLess(sl, 100)
        self.assertGreater(tp, 100)

    def test_calculate_atr_invalid(self):
        manager = AdaptiveSLManager()
        candles = [{"high": 1, "low": 1, "close": 1}] * 15
        with self.assertRaises(ValueError):
            manager.calculate_atr(candles)

# if __name__ == "__main__":
#     unittest.main()


# === from test_system_monitor.py ===
# test_system_monitor.py
import unittest
# from system_monitor import SystemMonitor

class DummyGUI:
    def __init__(self):
        self.running = True
        self.feed_status = None

    def update_feed_status(self, ok: bool, reason=None) -> None:
        self.feed_status = ok

    def update_api_status(self, ok: bool, reason=None) -> None:
        pass

    def log_event(self, msg: str) -> None:
        pass

class SystemMonitorStateTest(unittest.TestCase):
    def test_pause_and_resume(self):
        gui = DummyGUI()
        mon = SystemMonitor(gui)
        mon._handle_feed_down("lost")
        self.assertFalse(gui.running)
        self.assertFalse(mon._feed_ok)
        self.assertEqual(gui.feed_status, False)
        mon._handle_feed_up()
        self.assertTrue(gui.running)
        self.assertTrue(mon._feed_ok)
        self.assertEqual(gui.feed_status, True)

# if __name__ == '__main__':
#     unittest.main()


