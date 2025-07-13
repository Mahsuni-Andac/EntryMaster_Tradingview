# EntryMaster Trading Bot

EntryMaster ist ein vereinfachter Trading-Bot, der Binance Spot als einzige Quelle
für Marktdaten nutzt und alle Aufträge ausschließlich über BitMEX ausführt. Die
Handelslogik basiert auf einem TradingView-Indikator und läuft wahlweise im Live-
 oder Paper-Modus. Eine kleine Tkinter-GUI dient zur Konfiguration und Anzeige der
Handelsergebnisse.

## Eigenschaften
* Preisfeed über **python-binance** (BTCUSDT)
* Wählbare Marktdatenquelle: REST, WebSocket oder Auto
* Im **Auto-Modus** wird zuerst der WebSocket-Stream verwendet und bei Problemen
  automatisch auf REST umgeschaltet
* Orderausführung über die vorhandene **BitmexTrader**-Klasse
* Symbolmapping: `BTCUSDT` → `XBTUSD` mittels `bitmex_symbol()`
* Optionaler Paper-Trading-Modus mit realistischer PnL-Berechnung
* Umschaltbarer Live-Trading-Modus über die GUI
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
hinterlegt sind. Dort lässt sich auch die Option `data_source_mode` setzen:

- `websocket` – nutze ausschließlich den Binance WebSocket
- `rest` – nutze ausschließlich REST-Requests
- `auto` – versuche WebSocket und falle auf REST zurück


## Starten
```bash
python main.py
```
Die GUI fragt die BitMEX-Zugangsdaten ab und zeigt fortlaufend die Binance-Spot-
Preise sowie die Entwicklung des Paper-Trading-Kontos an. Über einen Schalter kann jederzeit vom Simulationsmodus in den Live-Betrieb gewechselt werden.

## Datenquellen & Modus

Der Bot kann Binance-Marktdaten über einen WebSocket-Stream oder per REST-API beziehen.
In der GUI lässt sich der Modus zwischen **WebSocket**, **REST** und **Auto** auswählen.
Im Auto-Modus versucht der Bot zunächst den WebSocket-Stream und schaltet bei
Problemen automatisch auf REST um. Der aktuell verwendete Modus wird in der GUI
live angezeigt:

- **🟢 WebSocket kommt an** – Stream aktiv
- **🔴 REST kommt an** – Fallback auf REST

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
  - Neben dem Systemstatus wird live angezeigt, ob die Binance-Daten 
    per WebSocket oder REST empfangen werden.
  - Die Anzeige passt sich automatisch an und ist farblich markiert.
  - Beispiele:
    - `✅ Alle Systeme laufen fehlerfrei | 🟢 WebSocket kommt an`
    - `✅ Alle Systeme laufen fehlerfrei | 🔴 REST kommt an`

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

