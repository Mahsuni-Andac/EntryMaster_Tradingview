# trade_executor.py

import time
import hmac
import hashlib
import requests
import os
import random  # <--- Fehlte, jetzt ergänzt
import logging
from config import SETTINGS

BASE_URL = "https://api.mexc.com"

API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_API_SECRET")

def sign_request(params, secret):
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

# --- Argumente akzeptieren ---
def place_order(
    symbol,
    direction,
    size,
    stop_loss,
    take_profit,
    multiplier=20,
    capital=1000,
    entry_price=None
):
    # entry_price-Check
    if entry_price is None or entry_price == 0:
        raise ValueError("entry_price muss gesetzt und > 0 sein!")

    # Slippage, Spread und Gebühren berücksichtigen
    slippage = random.uniform(-0.0005, 0.0005)  # ±0.05%
    spread = 0.0003  # 0.03%
    fee = 0.0002     # 0.02%
    effective_entry = entry_price * (1 + slippage + spread)
    size = capital * multiplier / entry_price
    fee_amount = effective_entry * size * fee

    # Eingesetztes Kapital (Margin) merken
    margin = capital

    # Übergabe von SL/TP (Argumente müssen IMMER gesetzt sein!)
    if stop_loss is None:
        stop_loss = 0
    if take_profit is None:
        take_profit = 0

    position = {
        "entry": effective_entry,
        "size": size,
        "sl": stop_loss,
        "tp": take_profit,
        "fee": fee_amount,
        "direction": direction,
        "margin": margin,
    }
    return position  # Rückgabewert zur Kontrolle

def open_position(position):
    """
    Öffnet eine Long- oder Short-Position.
    Im Testmodus: Log-Ausgabe.
    Im Live-Modus: MEXC MARKET-Order.
    """

    side = "BUY" if position["direction"] == "long" else "SELL"
    quantity = position["size"]
    symbol = SETTINGS["symbol"]

    timestamp = int(time.time() * 1000)
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": timestamp
    }
    params["signature"] = sign_request(params, API_SECRET)

    headers = {
        "X-MEXC-APIKEY": API_KEY
    }

    try:
        response = requests.post(f"{BASE_URL}/api/v3/order", params=params, headers=headers)
        response.raise_for_status()
        print(f"✅ LIVE-Order gesendet: {side} {symbol} | Größe: {quantity}")
        print(f"Antwort: {response.json()}")
    except Exception as e:
        print(f"❌ Fehler beim Platzieren der Live-Order: {e}")

def close_position(position, exit_price):
    """
    Schliesst eine aktive Position.
    """
    direction = position['direction'].upper()
    pnl = calculate_pnl(position, exit_price)

    print(f"🛑 [LIVE] Position {direction} soll geschlossen werden – Logik für Exit-Orders muss ggf. ergänzt werden.")
        # Option: `reduceOnly` MARKET-Order senden, z. B. via /order

def calculate_pnl(position, exit_price):
    """Berechnet den realistischen PnL einer Futures-Position.

    Die Berechnung folgt dem Prinzip:

    ``PnL = (Exit - Entry) / Entry * Leverage * Margin``

    Bei Short-Positionen wird die Kursdifferenz umgekehrt. Gebühren
    (Position['fee']) werden berücksichtigt.
    """

    entry = position["entry"]
    size = position["size"]
    leverage = SETTINGS.get("leverage", 1)
    margin = position.get("margin", size * entry / leverage)

    direction = 1 if position["direction"] == "long" else -1
    pnl = (exit_price - entry) / entry * leverage * margin * direction

    # Gebühren abziehen, falls vorhanden
    fee = position.get("fee", 0)
    pnl -= fee

    if pnl > margin:
        logging.warning("PnL > 100% des Einsatzes – Plausibilitätscheck")

    return pnl

if __name__ == "__main__":
    # --- Beispiel-Aufruf ---
    # Sicherstellen, dass take_profit korrekt übergeben wird!
    tp = trade.get("tp") or trade.get("take_profit") or 0
    sl = trade.get("sl") or trade.get("stop_loss") or 0

    position = place_order(
        symbol=symbol,
        direction=direction,
        size=size,
        stop_loss=sl,
        take_profit=tp,
        multiplier=multiplier,
        capital=capital,
        entry_price=entry_price,
    )

    open_position(position)
