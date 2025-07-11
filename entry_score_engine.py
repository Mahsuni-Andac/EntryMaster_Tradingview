# entry_score_engine.py

import numpy as np

def calculate_entry_score(candle, indicators, config):
    """
    Berechnet einen modular gewichteten Entry-Score basierend auf RSI, Volumen, Engulfing, Breakout.
    """
    score = 0.0
    total_weight = 0.0
    details = {}

    modules = [
        ("rsi", lambda: 1.0 if (
            indicators["rsi"] < config.get("rsi_long_threshold", 35) or
            indicators["rsi"] > config.get("rsi_short_threshold", 65)
        ) else 0.0),
        ("volume", lambda: 1.0 if indicators.get("volume_spike") else 0.0),
        ("engulfing", lambda: 1.0 if indicators.get("engulfing") else 0.0),
        ("breakout", lambda: 1.0 if indicators.get("breakout") else 0.0),
    ]

    for key, func in modules:
        weight_key = f"{key}_weight"
        if key in indicators and weight_key in config:
            val = func()
            weighted = val * config[weight_key]
            details[key] = weighted
            score += weighted
            total_weight += config[weight_key]

    final_score = round(score / total_weight, 3) if total_weight > 0 else 0.0
    return final_score, details
