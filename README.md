# EntryMaster Trading Bot

EntryMaster ist ein vereinfachter Trading-Bot, der Binance Spot als einzige Quelle
für Marktdaten nutzt und alle Aufträge ausschließlich über BitMEX ausführt. Die
Handelslogik basiert auf einem TradingView-Indikator und läuft wahlweise im Live-
 oder Paper-Modus. Eine kleine Tkinter-GUI dient zur Konfiguration und Anzeige der
Handelsergebnisse.

## Eigenschaften
* Preis- und Candlefeed ausschließlich über **python-binance** WebSocket (BTCUSDT)
* Der Bot empfängt 1-Minuten-Candles via `btcusdt@kline_1m` und zeigt nur abgeschlossene Kerzen an. REST wurde komplett entfernt.
* Orderausführung über die vorhandene **BitmexTrader**-Klasse
* Symbolmapping: `BTCUSDT` → `XBTUSD` mittels `bitmex_symbol()`
* Optionaler Paper-Trading-Modus mit realistischer PnL-Berechnung
* Umschaltbarer Live-Trading-Modus über die GUI
* Keine Unterstützung für andere Börsen
* ✅ **WebSocket Live Feed**: Der Bot nutzt einen stabilen WebSocket-Stream (BTCUSDT) von Binance zur Entscheidungsfindung. Kein REST notwendig. Vollständig in die GUI eingebunden.

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
hinterlegt sind. Der Eintrag `data_source_mode` ist fest auf `websocket`
gesetzt und sollte nicht verändert werden.


## Starten
```bash
python main.py
```
Die GUI fragt die BitMEX-Zugangsdaten ab und zeigt fortlaufend die Binance-Spot-
Preise sowie die Entwicklung des Paper-Trading-Kontos an. Über einen Schalter kann jederzeit vom Simulationsmodus in den Live-Betrieb gewechselt werden.

## 📡 Datenquelle

Der EntryMaster Bot nutzt WebSocket-Preisdaten und 1m-Candle-Daten von Binance BTCUSDT.

Dieser Bot arbeitet ausschließlich mit Live-Marktdaten von Binance BTCUSDT über
die WebSocket-API. REST-Zugriffe wurden entfernt, um maximale
Echtzeitpräzision zu gewährleisten. Sowohl Preis- als auch Candle-Daten werden nur per WebSocket bezogen.
Der Preisfeed wird niemals über andere Börsen gespeist. BitMEX dient nur zur Orderausführung bei Live-Trading.

### 📡 WebSocket-only Betrieb

Der Bot nutzt **ausschließlich WebSocket** für Binance BTCUSDT Marktdaten.
REST wurde entfernt, um saubere Candle-Daten sicherzustellen.

- ✅ Stream: `kline_1m`
- ✅ Nur abgeschlossene Candles (`x == True`) werden verarbeitet
- ✅ Anzeige in GUI + Log: "Marktdaten kommen an"

#### ⚠️ Hinweise
- Wenn keine Candle-Daten angezeigt werden, prüfe:
  - Verbindung zur Binance API
  - Ob der `kline`-Stream verwendet wird und nicht `@trade`
  - Ob `kline['x'] == True` korrekt überprüft wird

## Trading-Modi: Paper vs. Live

- **Einstieg & Ausstieg erfolgen immer anhand echter Binance BTCUSDT Marktdaten**
- Die Handelsentscheidung basiert auf dem integrierten EntryMaster-Indikator
- Zwei Modi:
  - 🧪 **Paper Trading** (Standard):
    - Trades werden simuliert
    - PnL, Kapitalverlauf und Logik sind identisch zum Live-Modus
    - Keine echte Orderausführung – auch bei gesetzten BitMEX-Keys
  - 💼 **Live Trading**:
    - Orderausführung über BitMEX (XBTUSD)
    - Nur aktiv, wenn der Schalter umgelegt und gültige API-Keys vorhanden sind

- In der GUI befindet sich ein klar gekennzeichneter Toggle-Switch zur Moduswahl
- Das System ist **fehlertolerant** – im Paper-Modus sind echte Trades **technisch ausgeschlossen**

## 📡 Live-Marktdaten-Anzeige (BTCUSDT)

- Der Bot verwendet echte Binance Spot-Marktdaten (BTCUSDT) zur Berechnung aller Entry/Exit-Signale.
- In der GUI wird der aktuelle BTCUSDT-Preis in Echtzeit angezeigt – aktualisiert alle 1–2 Sekunden.
- Diese Anzeige dient als Live-Status zur Preisreferenz für Nutzer und zur Verifikation des Systemzustands.
- Bei Verbindungsproblemen wird "❌" angezeigt.

## 🖥️ Grafische Oberfläche (GUI)

### ✅ Live-Status & Systemanzeige

- **Marktdatenstatus**:
  - In der GUI wird angezeigt, ob Binance BTCUSDT-Marktdaten erfolgreich empfangen werden.
  - Beispiel: `✅ Marktdaten kommen an`

- **Wirksamkeitsstatus**:
  - Direkt daneben wird der Zustand des Systems bewertet.
  - Beispiel: `✅ Alle Systeme laufen fehlerfrei` oder `❌ System macht Fehler!`
- **Datenfeed-Modusanzeige**:
  - Neben dem Systemstatus wird live angezeigt, ob der WebSocket verbunden ist.
  - Die Anzeige passt sich automatisch an und ist farblich markiert.
  - Beispiel:
    - `✅ Alle Systeme laufen fehlerfrei | 🟢 WebSocket verbunden`

- **Fehleranzeige im Log**:
  - Wenn ein Problem erkannt wird, erscheint unten im GUI-Log ein Eintrag mit Zeitstempel und Fehlerursache – aber nur einmal pro Fehler (kein Spam).

### 🌐 Statusanzeige: System-Glühbirnen

- Rechts in der GUI befindet sich eine eigene Status-Spalte mit Glühbirnen-Icons
  für jede wichtige Komponente.
- Der Status wird farblich angezeigt (Grün/Rot) und live aktualisiert.
- Beispiele:
  - ✅ Preisfeed OK
  - ✅ Paper-Trading aktiv
  - ❌ BitMEX API nicht gesetzt
- Bei vielen Einträgen wird eine **zweite Spalte automatisch erzeugt**, um alle
  Informationen sichtbar zu halten – ohne Scrollen oder Abschneiden.

