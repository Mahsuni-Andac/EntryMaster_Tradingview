# config.py

"""Default trading bot configuration."""

BINANCE_SYMBOL = "BTCUSDT"
BINANCE_INTERVAL = "1m"

SETTINGS = {
    "symbol": BINANCE_SYMBOL,
    "interval": BINANCE_INTERVAL,
    "starting_balance": 2000,
    "leverage": 10,
    "stop_loss_atr_multiplier": 0.75,
    "take_profit_atr_multiplier": 1.5,
    "multiplier": 10,
    "auto_multiplier": False,
    "capital": 2000,
    "version": "V10.4_Pro",
    "paper_mode": True,
    "data_source_mode": "websocket",
    "auto_partial_close": True,
    "partial_close_pct": 0.25,
    "apc_min_profit": 20,
    "risk_per_trade": 3.0,
    "drawdown_pct": 15.0,
    "max_drawdown": 300,
    "max_loss": 60,
    "cooldown": 2,
    "cooldown_after_exit": 120,
    "sl_tp_mode": "adaptive",
    "opt_session_filter": False,
    "sl_tp_manual_active": True,
    "manual_sl": 0.75,
    "manual_tp": 1.5,
}
