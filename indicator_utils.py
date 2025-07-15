# indicator_utils.py

def calculate_ema(values, length, round_result=False):
    if not values or len(values) < length:
        return None

    k = 2 / (length + 1)
    ema = values[0]
    for price in values[1:]:
        ema = price * k + ema * (1 - k)

    return round(ema, 2) if round_result else ema


def calculate_rsi(close, low, high):
    if high - low == 0:
        return 50

    midpoint = (high + low) / 2
    relative = (close - midpoint) / (high - low)
    rsi = 50 + (relative * 50)
    return max(0, min(100, rsi))


def calculate_atr(candles, length):
    candles = [
        c
        for c in candles
        if all(k in c and c[k] is not None for k in ("high", "low", "close"))
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


def calculate_volatility_score(candle, atr):
    candle_range = candle["high"] - candle["low"]
    return round(candle_range / atr, 2) if atr else 0


def macd_crossover_detected(closes, short=12, long=26, signal=9):
    if len(closes) < long + signal + 1:
        return False

    def ema(values, length):
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
