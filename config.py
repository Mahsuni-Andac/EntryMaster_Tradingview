# config.py

BINANCE_SYMBOL = "BTCUSDT"
BINANCE_INTERVAL = "1m"

SETTINGS = {
    "symbol": BINANCE_SYMBOL,
    "interval": BINANCE_INTERVAL,
    "starting_balance": 1000,
    "leverage": 20,
    "stop_loss_atr_multiplier": 0.5,
    "take_profit_atr_multiplier": 1.5,
    "use_session_filter": False,
    "session_filter": {
        "allowed": ["london", "new_york"],
        "use_utc": True,
        "debug": False,
    },
    "multiplier": 20,
    "auto_multiplier": False,
    "capital": 1000,
    "version": "V10.4_Pro",
    "paper_mode": True,
    "data_source_mode": "websocket",
}
