from andac_entry_master import AndacEntryMaster, AndacSignal

_MASTER: AndacEntryMaster | None = None


def should_enter(candle: dict, indicator: dict, config: dict) -> AndacSignal:
    global _MASTER
    if _MASTER is None:
        _MASTER = AndacEntryMaster(
            lookback=config.get("lookback", 20),
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
