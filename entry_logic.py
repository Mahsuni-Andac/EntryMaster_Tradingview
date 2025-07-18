from andac_entry_master import AndacSignal
import numpy as np

def should_enter(candle, indicator, config) -> AndacSignal:
    close = candle["close"]
    open_ = candle["open"]
    high = candle["high"]
    low = candle["low"]
    volume = candle["volume"]

    lookback = config.get("lookback", 20)
    puffer = config.get("puffer", 10.0)
    vol_mult = config.get("volumen_factor", 1.0)
    rsi = indicator.get("rsi", 50)
    atr = indicator.get("atr", 1)

    # Optionen
    opt_engulf = config.get("opt_engulf", False)
    opt_mtf_confirm = config.get("opt_mtf_confirm", False)
    opt_volumen_strong = config.get("opt_volumen_strong", False)
    opt_rsi_ema = config.get("opt_rsi_ema", False)
    opt_safe_mode = config.get("opt_safe_mode", False)
    opt_confirm_delay = config.get("opt_confirm_delay", False)
    opt_engulf_bruch = config.get("opt_engulf_bruch", False)
    opt_engulf_big = config.get("opt_engulf_big", False)

    # Zusatzindikatoren
    mtf_ok = indicator.get("mtf_ok", True)
    prev_close = indicator.get("prev_close", close)
    prev_open = indicator.get("prev_open", open_)
    prev_rsi = indicator.get("prev_rsi", rsi)
    high_prev = indicator.get("high_lookback", high)
    low_prev = indicator.get("low_lookback", low)
    avg_vol = indicator.get("avg_volume", volume)
    prev_bull_signal = indicator.get("prev_bull_signal", False)
    prev_baer_signal = indicator.get("prev_baer_signal", False)

    bruch_oben = high > high_prev + puffer
    bruch_unten = low < low_prev - puffer
    big_candle = abs(close - open_) > atr
    vol_spike = volume > avg_vol * vol_mult and big_candle

    bull_engulfing = close > open_ and prev_close < prev_open and close > prev_open and open_ < prev_close
    baer_engulfing = close < open_ and prev_close > prev_open and close < prev_open and open_ > prev_close

    engulf_long = bull_engulfing and (not opt_engulf_bruch or bruch_oben) and (not opt_engulf_big or big_candle)
    engulf_short = baer_engulfing and (not opt_engulf_bruch or bruch_unten) and (not opt_engulf_big or big_candle)

    long_valid = bruch_oben and (not opt_volumen_strong or vol_spike) and (not opt_rsi_ema or rsi > 50)
    short_valid = bruch_unten and (not opt_volumen_strong or vol_spike) and (not opt_rsi_ema or rsi < 50)

    if opt_safe_mode:
        if rsi < 30:
            long_valid = False
        if rsi > 70:
            short_valid = False

    if opt_engulf:
        if not engulf_long:
            long_valid = False
        if not engulf_short:
            short_valid = False

    if opt_mtf_confirm and not mtf_ok:
        long_valid = short_valid = False

    if opt_confirm_delay:
        long_final = prev_bull_signal and close > open_
        short_final = prev_baer_signal and close < open_
    else:
        long_final = long_valid
        short_final = short_valid

    engulf = bull_engulfing if long_final else baer_engulfing if short_final else False
    if long_final:
        return AndacSignal(signal="long", rsi=rsi, vol_spike=vol_spike, engulfing=engulf)
    elif short_final:
        return AndacSignal(signal="short", rsi=rsi, vol_spike=vol_spike, engulfing=engulf)
    else:
        return AndacSignal(signal=None, rsi=rsi, vol_spike=vol_spike, engulfing=engulf, reasons=["No signal conditions met"])
