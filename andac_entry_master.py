"""Andac Entry-Master Indikatorimplementierung.

Portierung des TradingView Pine Script Indikators
"🤑 Andac Entry-Master 🚀 BTC-Futures-Binance" nach Python.

Die Klasse bietet eine `evaluate`-Methode, die
auf Basis neuer Candle-Daten Long- oder Short-Signale liefert.
Alle Parameter des Originals sind als Attribute verfügbar und
können bei der Instanziierung angepasst werden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict

from data_provider import fetch_latest_candle


@dataclass
class AndacSignal:
    """Ergebnis eines Indikatoraufrufs."""

    signal: Optional[str]  # "long", "short" oder None
    rsi: float
    vol_spike: bool
    engulfing: bool
    reasons: List[str] = field(default_factory=list)


class AndacEntryMaster:
    """Python-Port des TradingView Indikators."""

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

    # ---- Hilfsfunktionen -------------------------------------------------
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

    # ---- Kernlogik -------------------------------------------------------
    def evaluate(self, candle: Dict[str, float], symbol: str = "BTCUSDT") -> AndacSignal:
        """Analysiert die übergebene Kerze und gibt ggf. ein Entry-Signal zurück."""

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
            mtf = fetch_latest_candle(symbol, "15m")
            if mtf:
                mtf_ok = (mtf["close"] > mtf["open"]) == (candle["close"] > candle["open"])

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

        # --- Filterentscheidungen sammeln ---
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

