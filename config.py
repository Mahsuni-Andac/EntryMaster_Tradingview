# config.py

SETTINGS = {
    "symbol": "BTC_USDT",
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
    "version": "V10.4_Pro",
}
