# config.py

SETTINGS = {
    "symbol": "BTCUSDT",
    "interval": "1m",
    "starting_balance": 1000,
    "leverage": 20,
    "stop_loss_atr_multiplier": 0.5,
    "take_profit_atr_multiplier": 1.5,
    "use_session_filter": False,
    "test_mode": False,            # 🧪 Kein Live-Trade
    "trading_backend": "sim",      # 🔁 "mexc", "andac", "sim"
    "multiplier": 20,
    "auto_multiplier": False,
    "capital": 1000,
    "sim_data_path": "sim_data.csv",
    "dydx_api_url": "https://api.dydx.trade/v4",
    "version": "EntryMaster_Tradingview",
    # Parameter des Andac Entry-Master Indikators
    "andac_config": {
        "lookback": 20,
        "puffer": 10.0,
        "vol_mult": 1.2,
        "opt_tpsl": True,
        "opt_rsi_ema": False,
        "opt_safe_mode": False,
        "opt_engulf": False,
        "opt_engulf_bruch": False,
        "opt_engulf_big": False,
        "opt_confirm_delay": False,
        "opt_mtf_confirm": False,
        "opt_volumen_strong": False,
        "opt_session_filter": False,
    },
}
