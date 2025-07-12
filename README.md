# EntryMaster Trading Bot

EntryMaster ist ein vereinfachter Trading-Bot, der Binance Spot als einzige Quelle
für Marktdaten nutzt und alle Aufträge ausschließlich über BitMEX ausführt. Die
Handelslogik basiert auf einem TradingView-Indikator und läuft wahlweise im Live-
 oder Paper-Modus. Eine kleine Tkinter-GUI dient zur Konfiguration und Anzeige der
Handelsergebnisse.

## Eigenschaften
* Preisfeed über **python-binance** (BTCUSDT)
* Orderausführung über die vorhandene **BitmexTrader**-Klasse
* Symbolmapping: `BTCUSDT` → `XBTUSD` mittels `bitmex_symbol()`
* Optionaler Paper-Trading-Modus mit realistischer PnL-Berechnung
* Keine Unterstützung für andere Börsen

## Installation
1. Python 3.10 oder neuer installieren
2. Abhängigkeiten installieren:
   ```bash
   pip install python-binance websocket-client
   ```
3. BitMEX API-Schlüssel als Umgebungsvariablen setzen:
   `BITMEX_API_KEY` und `BITMEX_API_SECRET`

## Beispielkonfiguration
Die Datei `config.py` enthält alle wichtigen Parameter. Standardmäßig wird mit
`BTCUSDT` gehandelt und der Paper-Modus ist aktiv, solange keine API-Schlüssel
hinterlegt sind.

## Starten
```bash
python main.py
```
Die GUI fragt die BitMEX-Zugangsdaten ab und zeigt fortlaufend die Binance-Spot-
Preise sowie die Entwicklung des Paper-Trading-Kontos an.

