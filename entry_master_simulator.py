# entry_master_simulator.py
#
# Changelog
# - Adapted to ``EntryDecision`` dataclass return
# - Minor formatting improvements

"""Simple offline simulator for the entry engine."""

import csv
import time
from entry_master_engine import EntryMasterEngine
from pnl_utils import check_plausibility

class EntryMasterSimulator:
    def __init__(self, config, candles, initial_balance=1000):
        self.engine = EntryMasterEngine(config, mode="sim")
        self.candles = candles
        self.config = config
        self.balance = initial_balance
        self.saved_profit = 0.0
        self.position = None
        self.closed_trades = []
        self.history = []

    def run(self):
        for idx, candle in enumerate(self.candles):
            context = self._build_context(idx)
            signal = self.engine.evaluate_entry(candle, context)
            self.engine.tick()

            if self.position:
                closed, reason = self._check_exit(candle)
                if closed:
                    self._close_position(candle, reason)
                    continue

            if not self.position and signal.entry_type:
                self._open_position(candle, signal, context)

    def _open_position(self, candle, signal, context):
        entry_price = candle["close"]
        # Positionsgröße entspricht immer dem eingesetzten Kapital (Margin)
        size = self.balance
        sl = signal.sl
        tp = self._calc_tp(entry_price, sl, signal.entry_type)

        self.position = {
            "type": signal.entry_type,
            "entry": entry_price,
            "sl": sl,
            "tp": tp,
            "size": size,
            "leverage": self.config.get("leverage", 1),
            "open_idx": len(self.history)
        }
        print(
            f"ENTRY {signal.entry_type.upper()} @ {entry_price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}"
        )

    def _check_exit(self, candle):
        if not self.position:
            return False, None
        p = self.position
        if p["type"] == "long":
            if candle["low"] <= p["sl"]:
                self.engine.register_sl()
                return True, "SL"
            if candle["high"] >= p["tp"]:
                return True, "TP"
        if p["type"] == "short":
            if candle["high"] >= p["sl"]:
                self.engine.register_sl()
                return True, "SL"
            if candle["low"] <= p["tp"]:
                return True, "TP"
        return False, None

    def _close_position(self, candle, reason):
        p = self.position
        exit_price = p["sl"] if reason == "SL" else p["tp"]
        direction = 1 if p["type"] == "long" else -1
        pnl = (
            (exit_price - p["entry"]) / p["entry"]
            * p.get("leverage", 1)
            * p["size"]
            * direction
        )
        old_balance = self.balance
        self.balance += pnl
        check_plausibility(pnl, old_balance, self.balance, p["size"])
        if self.balance > self.config["start_capital"]:
            self.saved_profit += (self.balance - self.config["start_capital"]) * 0.7
            self.balance = self.config["start_capital"] + (self.balance - self.config["start_capital"]) * 0.3
        print(
            f"EXIT {p['type'].upper()} {reason} @ {exit_price:.2f} | "
            f"Entry: {p['entry']:.2f} | Size: {p['size']:.2f} | Lev: x{p.get('leverage',1)} | "
            f"PnL: {pnl:.2f} | Balance: {old_balance:.2f} -> {self.balance:.2f}"
        )
        self.closed_trades.append({**p, "exit": exit_price, "reason": reason, "pnl": pnl})
        self.position = None

    def _build_context(self, idx):
        hist = self.candles[max(0, idx-20):idx]
        close_hist = [c["close"] for c in hist] if hist else [0]
        ema = sum(close_hist[-self.config.get("ema_length", 20):]) / self.config.get("ema_length", 20)
        # Dummy: Support/Resis = letzter Low/High der History
        support = min(c["low"] for c in hist) if hist else 0
        resistance = max(c["high"] for c in hist) if hist else 0
        momentum = (close_hist[-1] - close_hist[0]) if len(close_hist) > 1 else 0

        return {
            "history": hist,
            "ema": ema,
            "support": support,
            "resistance": resistance,
            "momentum": momentum
        }

    def _calc_tp(self, entry, sl, t):
        risk = abs(entry - sl)
        reward = risk * self.config.get("rr_ratio", 2)
        return entry + reward if t == "long" else entry - reward

# Beispiel-Nutzung für Test:
# with open("sim_data.csv") as f:
#     data = list(csv.DictReader(f))
#     candles = [{k: float(row[k]) if k != "time" else row[k] for k in row} for row in data]
# sim = EntryMasterSimulator(config={"leverage": 20, "start_capital": 1000}, candles=candles)
# sim.run()
