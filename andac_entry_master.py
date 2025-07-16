# andac_entry_master.py

from __future__ import annotations

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

        self.candles: List[Dict[str, float]] = []
        self.prev_bull_signal = False
        self.prev_bear_signal = False

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

    def evaluate(self, candle: Dict[str, float], symbol: str = "BTCUSDT") -> AndacSignal:

        self.candles.append(candle)
        if len(self.candles) > self.lookback + 20:
            self.candles.pop(0)
        if len(self.candles) < self.lookback + 2:
            return AndacSignal(None, 50.0, False, False)

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
        import bitmex_interface as bm
        return bm.place_order(side, quantity, reduce_only=reduce_only, order_type=order_type)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("open_position failed: %s", exc)
        return None


def close_position() -> Optional[dict]:
    try:
        import bitmex_interface as bm
        return bm.close_position()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("close_position failed: %s", exc)
        return None


def close_partial_position(volume: float, order_type: str = "Market") -> Optional[dict]:
    if volume <= 0:
        return None
    try:
        import bitmex_interface as bm
        position = bm.get_open_position()
        if not position:
            return None
        side = "Sell" if position["currentQty"] > 0 else "Buy"
        return bm.place_order(side, abs(volume), reduce_only=True, order_type=order_type)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# AutoRecommender (from auto_recommender.py)
class AutoRecommender:
    def __init__(self, gui: Any, interval: int = 10) -> None:
        self.gui = gui
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False

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

    def _run(self) -> None:
        while self._running:
            if (
                getattr(self.gui, "running", False)
                and hasattr(self.gui, "auto_apply_recommendations")
                and self.gui.auto_apply_recommendations.get()
            ):
                try:
                    self.gui.apply_recommendations()
                except Exception as exc:
                    if hasattr(self.gui, "log_event"):
                        self.gui.log_event(f"\u26A0\uFE0F Auto-Empfehlung Fehler: {exc}")
            time.sleep(self.interval)


# ---------------------------------------------------------------------------
# RiskManager (from risk_manager.py)
class RiskManager:
    def __init__(self, gui: Any, start_capital: Optional[float] = None) -> None:
        self.gui = gui
        self.start_capital = start_capital or 0.0
        self.current_capital = start_capital or 0.0
        self.highest_capital = start_capital or 0.0
        self.total_loss = 0.0
        self.max_risk = 3.0
        self.drawdown_limit = 15.0
        self.max_loss = 0.0
        self.max_drawdown = 0.0
        self.drawdown_pct = 0.0

    def set_limits(self, max_risk: float, drawdown_limit: float) -> None:
        self.max_risk = max_risk
        self.drawdown_limit = drawdown_limit

    def configure(self, **cfg: Any) -> None:
        for key, value in cfg.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def set_start_capital(self, capital: float) -> None:
        self.start_capital = capital
        self.current_capital = capital
        self.highest_capital = capital
        self.total_loss = 0.0

    def update_capital(self, capital: float) -> None:
        self.current_capital = capital
        if capital > self.highest_capital:
            self.highest_capital = capital

    def update_loss(self, pnl: float) -> None:
        if pnl < 0:
            self.total_loss += abs(pnl)

    def check_loss_limit(self) -> bool:
        return self.max_loss > 0 and self.total_loss >= self.max_loss

    def check_drawdown_limit(self) -> bool:
        if self.max_drawdown <= 0:
            return False
        return (self.start_capital - self.current_capital) >= self.max_drawdown

    def check_drawdown_pct_limit(self) -> bool:
        if self.drawdown_pct <= 0 or self.start_capital == 0:
            return False
        dd_pct = (self.start_capital - self.current_capital) / self.start_capital * 100
        return dd_pct >= self.drawdown_pct

    def is_risk_too_high(self, expected_loss: float, capital: float) -> bool:
        return expected_loss > capital * (self.max_risk / 100)

    def register_loss(self, loss_amount: float) -> bool:
        self.total_loss += loss_amount
        return self.get_drawdown_percent() < self.drawdown_limit

    def get_drawdown_percent(self) -> float:
        if self.start_capital == 0:
            return 0.0
        return (self.total_loss / self.start_capital) * 100


# ---------------------------------------------------------------------------
# BaseWebSocket & BinanceCandleWebSocket (from binance_ws.py)
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
            import global_state
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
# SignalWorker (from signal_worker.py)
class SignalWorker:
    def __init__(self, handler: Callable[[dict], Any], queue_obj: Optional[queue.Queue] = None, maxsize: int = 100) -> None:
        self.handler = handler
        self.queue: queue.Queue[dict] = queue_obj or queue.Queue(maxsize=maxsize)
        self._running = False
        self.thread: Optional[threading.Thread] = None
        self._last_submit: Optional[float] = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self._running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self._running = False

    def submit(self, candle: dict) -> None:
        now = time.time()
        self._last_submit = now
        try:
            self.queue.put_nowait(candle)
        except queue.Full:
            pass

    def _run(self) -> None:
        while self._running:
            try:
                candle = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                self.handler(candle)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Entry logic facade (from entry_logic.py)
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
    return _MASTER.evaluate(candle)


# ---------------------------------------------------------------------------
# Strategy filter helpers (from strategy.py)
_FILTER_CONFIG: Dict[str, Any] = {}


def set_filter_config(filters: Optional[Dict[str, Any]]) -> None:
    global _FILTER_CONFIG
    _FILTER_CONFIG = filters or {}


def get_filter_config() -> Dict[str, Any]:
    return _FILTER_CONFIG


