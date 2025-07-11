# indicator_utils.py

def calculate_ema(values, length, round_result=False):
    """
    📈 Berechnet den exponentiellen gleitenden Durchschnitt (EMA).
    """
    if not values or len(values) < length:
        return None

    k = 2 / (length + 1)
    ema = values[0]
    for price in values[1:]:
        ema = price * k + ema * (1 - k)

    return round(ema, 2) if round_result else ema


def calculate_rsi(close, low, high):
    """
    📊 Einfacher RSI-ähnlicher Impulsindikator basierend auf dem Verhältnis im High-Low-Range.
    """
    if high - low == 0:
        return 50

    midpoint = (high + low) / 2
    relative = (close - midpoint) / (high - low)
    rsi = 50 + (relative * 50)
    return max(0, min(100, rsi))


def calculate_atr(candles, length):
    """
    📏 Berechnet den Average True Range (ATR) basierend auf Candle-Daten.
    Erwartet: [{'high': ..., 'low': ..., 'close': ...}, ...]
    """
    if not candles or len(candles) < length:
        return None

    trs = []
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)

    return round(sum(trs[-length:]) / length, 2)


def calculate_volatility_score(candle, atr):
    """
    💥 Verhältnis von Candle-Range zu ATR (z. B. 1.2 = 120 % ATR).
    """
    candle_range = candle["high"] - candle["low"]
    return round(candle_range / atr, 2) if atr else 0
