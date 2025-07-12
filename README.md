# EntryMaster Trading Bot

Dieser Bot nutzt ausschließlich **Binance Spot** als Preisfeed für `BTCUSDT` und führt alle Trades über **BitMEX** (`XBTUSD`) aus. Die Handelslogik basiert auf einem TradingView-Indikator und wird über eine einfache Tkinter-GUI konfiguriert.

## Eigenschaften
- Preisabfrage über `python-binance`
- Orderausführung über die vorhandene `BitmexTrader`-Klasse
- Optionaler Paper-Trading-Modus mit realistischer PnL-Berechnung
- Keine Unterstützung für andere Börsen

## Installation
1. Python 3.10 oder neuer installieren
2. Abhängigkeiten installieren:
   ```bash
   pip install python-binance websocket-client
   ```
3. API-Schlüssel für BitMEX setzen (Umgebungsvariablen `BITMEX_API_KEY` und `BITMEX_API_SECRET`)

## Starten
```bash
python main.py
```
Die GUI erlaubt das Hinterlegen der BitMEX-Zugangsdaten und startet anschließend den Bot. Marktpreise werden live von Binance abgefragt.

## Symbolmapping
Für BitMEX wird `BTCUSDT` automatisch zu `XBTUSD` gemappt. Die Hilfsfunktion `bitmex_symbol()` übernimmt diese Umwandlung.
