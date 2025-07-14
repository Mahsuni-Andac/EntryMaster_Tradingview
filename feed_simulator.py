# feed_simulator.py
"""Offline candle feed for strategy testing."""

from __future__ import annotations

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
