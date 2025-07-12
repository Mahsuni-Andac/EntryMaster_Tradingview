# init_helpers.py
from config import SETTINGS

def import_trader(backend):
    """🔁 Gibt die passende Trader-Klasse für das angegebene Backend zurück."""
    try:
        if backend == "mexc":
            from mexc_trader import MEXCTrader
            return MEXCTrader
        elif backend == "andac":
            from andac_trader import AndacTrader
            return AndacTrader
        elif backend == "dydx":
            from dydx_trader import DYDXTrader, is_dydx_configured
            if not is_dydx_configured(SETTINGS):
                raise ValueError("dYdX nicht konfiguriert")
            return DYDXTrader
        elif backend == "binance":
            from binance_trader import BinanceTrader
            return BinanceTrader
        elif backend == "bybit":
            from bybit_trader import BybitTrader
            return BybitTrader
        else:
            raise ValueError
    except ImportError as e:
        raise ImportError(f"❌ Fehler beim Import des Traders für Backend '{backend}': {e}")
    except ValueError:
        raise ValueError(f"❌ Unbekanntes Trading-Backend: '{backend}'")


def calculate_ema(values, length):
    """📈 Berechnet den exponentiellen gleitenden Durchschnitt (EMA)."""
    if not values or len(values) < length:
        print(f"⚠️ Zu wenig Werte für EMA-{length}: nur {len(values)} vorhanden.")
        return None

    k = 2 / (length + 1)
    ema = values[0]
    for price in values[1:]:
        ema = price * k + ema * (1 - k)
    return ema


def normalize_symbol(symbol):
    """🔤 Entfernt Sonderzeichen aus Symbolnamen, z. B. BTC/USDT → BTC_USDT."""
    return symbol.replace("/", "").upper()
