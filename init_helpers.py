# init_helpers.py
from config import SETTINGS

def import_trader(backend):
    """🔁 Gibt die passende Trader-Klasse für das angegebene Backend zurück."""
    try:
        if backend == "bitmex":
            from bitmex_trader import BitmexTrader
            return BitmexTrader
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
    """🔤 Entfernt Sonderzeichen aus Symbolnamen, z. B. BTC/USDT → BTCUSDT."""
    return symbol.replace("/", "").upper()
