"""Paper Trading Engine using live MEXC data."""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, asdict
from typing import Optional, List

import requests


@dataclass
class Position:
    side: str
    size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    leverage: int
    open_time: float
    margin: float


@dataclass
class TradeLogEntry:
    timestamp: float
    type: str
    side: str
    price: float
    size: float
    leverage: int
    fee: float
    pnl: float
    reason: str = ""


class PaperTradingEngine:
    """Simuliert Futures-Trades möglichst realistisch."""

    def __init__(
        self,
        symbol: str = "BTC_USDT",
        leverage: int = 20,
        balance: float = 1000.0,
        db_path: str = "trades.sqlite",
        use_slippage: bool = True,
    ) -> None:
        self.symbol = symbol
        self.leverage = leverage
        self.balance = balance
        self.position: Optional[Position] = None
        self.trade_log: List[TradeLogEntry] = []
        self.fee_rate = 0.0004
        self.use_slippage = use_slippage
        self._db = sqlite3.connect(db_path)
        self._setup_db()

    def _setup_db(self) -> None:
        cur = self._db.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trades(
                timestamp REAL,
                type TEXT,
                side TEXT,
                price REAL,
                size REAL,
                leverage INTEGER,
                fee REAL,
                pnl REAL,
                reason TEXT
            )
            """
        )
        self._db.commit()

    def _log_trade(self, entry: TradeLogEntry) -> None:
        self.trade_log.append(entry)
        cur = self._db.cursor()
        cur.execute(
            "INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?)",
            (
                entry.timestamp,
                entry.type,
                entry.side,
                entry.price,
                entry.size,
                entry.leverage,
                entry.fee,
                entry.pnl,
                entry.reason,
            ),
        )
        self._db.commit()

    # --- MEXC Datenabfrage ---
    def _order_book(self) -> tuple[Optional[float], Optional[float]]:
        url = f"https://api.mexc.com/api/v3/depth?symbol={self.symbol}&limit=1"
        try:
            data = requests.get(url, timeout=10).json()
            bid = float(data["bids"][0][0])
            ask = float(data["asks"][0][0])
            return bid, ask
        except Exception as exc:
            logging.error("Orderbuch konnte nicht geladen werden: %s", exc)
            return None, None

    def _calculate_slippage(self, side: str, amount: float) -> float:
        """Berechnet Slippage in USD anhand des Orderbuchs."""
        try:
            data = requests.get(
                f"https://api.mexc.com/api/v3/depth?symbol={self.symbol}&limit=50",
                timeout=10,
            ).json()
            levels = data["asks"] if side == "long" else data["bids"]
            remaining = amount
            target_price = float(levels[0][0])
            for price, qty in levels:
                price = float(price)
                qty_usd = float(qty) * price
                target_price = price
                if qty_usd >= remaining:
                    break
                remaining -= qty_usd
            mid = (float(data["bids"][0][0]) + float(data["asks"][0][0])) / 2
            return target_price - mid if side == "long" else mid - target_price
        except Exception as exc:
            logging.error("Slippage-Berechnung fehlgeschlagen: %s", exc)
            return 0.0

    def get_funding_rate(self) -> float:
        """Ruft die aktuelle Funding Rate ab (0 bei Fehler)."""
        pair = self.symbol.replace("USDT", "_USDT")
        url = f"https://contract.mexc.com/api/v1/contract/fundingRate/{pair}"
        try:
            data = requests.get(url, timeout=10).json()
            return float(data["data"]["fundingRate"])
        except Exception as exc:
            logging.error("Funding Rate Fehler: %s", exc)
            return 0.0

    @staticmethod
    def calculate_pnl(
        entry_price: float,
        exit_price: float,
        leverage: int,
        margin: float,
        side: str,
    ) -> float:
        """Berechnet den PnL (ohne Fees) basierend auf Futures-Logik."""
        direction = 1 if side == "long" else -1
        change = (exit_price - entry_price) / entry_price * direction
        return change * leverage * margin

    # --- Handelsfunktionen ---
    def open_position(self, side: str, amount: float, sl: float, tp: float) -> None:
        """\
        Öffnet eine Position. ``amount`` ist das eingesetzte Kapital (Margin).
        Im Cross-Modus wird die Margin nicht vom Kontostand abgezogen,
        sondern nur als Basis für die PnL-Berechnung verwendet.
        """
        if self.position is not None:
            logging.warning("Es ist bereits eine Position offen")
            return

        bid, ask = self._order_book()
        if bid is None or ask is None:
            logging.warning("Kein Orderbuch verfügbar")
            return

        if self.use_slippage:
            # Slippage am Marktvolumen der gesamten Position (Margin * Leverage)
            slippage = self._calculate_slippage(side, amount * self.leverage)
            price = (ask + slippage) if side == "long" else (bid - slippage)
        else:
            price = ask * 1.0002 if side == "long" else bid * 0.9998

        size = amount * self.leverage / price
        fee = price * size * self.fee_rate
        required = amount + fee
        if self.balance < required:
            logging.warning("Nicht genügend Balance für diesen Trade")
            return

        # Bei Cross-Margin bleibt die eingesetzte Margin auf dem Konto,
        # nur die Gebühren werden sofort abgezogen.
        self.balance -= fee
        self.position = Position(
            side,
            size,
            price,
            sl,
            tp,
            self.leverage,
            time.time(),
            amount,
        )

        entry = TradeLogEntry(time.time(), "open", side, price, size, self.leverage, fee, 0.0)
        self._log_trade(entry)

    def close_position(self, reason: str = "manual") -> None:
        """Schließt die komplette Position und realisiert den PnL."""
        if not self.position:
            return

        bid, ask = self._order_book()
        if bid is None or ask is None:
            logging.warning("Kein Orderbuch verfügbar")
            return

        closing_side = "short" if self.position.side == "long" else "long"
        notional = self.position.margin * self.position.leverage
        if self.use_slippage:
            slippage = self._calculate_slippage(closing_side, notional)
            price = (bid - slippage) if self.position.side == "long" else (ask + slippage)
        else:
            price = bid * 0.9998 if self.position.side == "long" else ask * 1.0002

        gross_pnl = self.calculate_pnl(
            self.position.entry_price,
            price,
            self.position.leverage,
            self.position.margin,
            self.position.side,
        )
        if gross_pnl > self.position.margin:
            logging.warning("PnL > 100%%, bitte Werte prüfen")

        funding = self.get_funding_rate() * self.position.size * self.position.entry_price
        fee = price * self.position.size * self.fee_rate
        total_pnl = gross_pnl - fee + funding

        # Bei Cross-Margin wird nur der realisierte Gewinn/Verlust verbucht
        self.balance += total_pnl

        entry = TradeLogEntry(
            time.time(),
            "close",
            self.position.side,
            price,
            self.position.size,
            self.leverage,
            fee,
            total_pnl,
            reason,
        )
        self._log_trade(entry)
        self.position = None

    def partial_close(self, margin: float, reason: str = "partial") -> None:
        """Schließt einen Teil der offenen Position.

        Nur für den geschlossenen Anteil wird der PnL realisiert. Bei Cross-
        Margin verändert sich die Kontobalance also nur um diesen Gewinn oder
        Verlust. Die Restposition behält ihren ursprünglichen Entry-Preis.

        Parameters
        ----------
        margin : float
            Marginbetrag in USD, der geschlossen werden soll.
        reason : str
            Freier Text für das Log.
        """
        if not self.position or margin <= 0:
            return

        margin = min(margin, self.position.margin)
        bid, ask = self._order_book()
        if bid is None or ask is None:
            logging.warning("Kein Orderbuch verfügbar")
            return

        closing_side = "short" if self.position.side == "long" else "long"
        if self.use_slippage:
            # Slippage anhand des tatsächlichen Marktvolumens (Margin * Leverage)
            slippage = self._calculate_slippage(closing_side, margin * self.position.leverage)
            price = (bid - slippage) if self.position.side == "long" else (ask + slippage)
        else:
            price = bid * 0.9998 if self.position.side == "long" else ask * 1.0002

        # Futures-Kontraktgröße die reduziert wird
        size_to_close = margin * self.position.leverage / self.position.entry_price

        # Realisierten PnL nur für diese Teilgröße berechnen
        gross_pnl = self.calculate_pnl(
            self.position.entry_price,
            price,
            self.position.leverage,
            margin,
            self.position.side,
        )
        funding = self.get_funding_rate() * size_to_close * self.position.entry_price
        fee = price * size_to_close * self.fee_rate
        total_pnl = gross_pnl - fee + funding

        old_balance = self.balance
        # Nur der realisierte Gewinn/Verlust verändert die Balance
        self.balance += total_pnl

        self.position.margin -= margin
        self.position.size -= size_to_close

        log_entry = TradeLogEntry(
            time.time(),
            "partial",
            self.position.side,
            price,
            size_to_close,
            self.leverage,
            fee,
            total_pnl,
            reason,
        )
        self._log_trade(log_entry)

        # Optional: unrealisierten PnL der Restposition berechnen
        unrealized = 0.0
        if self.position.margin > 0:
            unrealized = self.calculate_pnl(
                self.position.entry_price,
                price,
                self.position.leverage,
                self.position.margin,
                self.position.side,
            )

        logging.info(
            "Teilverkauf: Entry %.2f Exit %.2f Größe %.4f RealPnL %.2f Fee %.2f | Bal %.2f -> %.2f | Rest %.4f | Unreal %.2f",
            self.position.entry_price,
            price,
            size_to_close,
            total_pnl,
            fee,
            old_balance,
            self.balance,
            self.position.size,
            unrealized,
        )

        if self.position.margin <= 0 or self.position.size <= 0:
            self.position = None

    def save_log(self, path: str = "tradelog_paper.csv") -> None:
        import csv

        if not self.trade_log:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=asdict(self.trade_log[0]).keys())
            writer.writeheader()
            for item in self.trade_log:
                writer.writerow(asdict(item))
