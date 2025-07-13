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
hinterlegt sind.

## Starten
```bash
python main.py
```
Die GUI fragt die BitMEX-Zugangsdaten ab und zeigt fortlaufend die Binance-Spot-
Preise sowie die Entwicklung des Paper-Trading-Kontos an. Über einen Schalter kann jederzeit vom Simulationsmodus in den Live-Betrieb gewechselt werden.

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

- **Fehleranzeige im Log**:
  - Wenn ein Problem erkannt wird, erscheint unten im GUI-Log ein Eintrag mit Zeitstempel und Fehlerursache – aber nur einmal pro Fehler (kein Spam).

- **Status-Glühbirnen (rechts)**:
  - Zeigen kompakten Überblick über Systemelemente wie:
    - BitMEX API verbunden
    - Paper-Trading aktiv
    - Preisfeed OK
    - Konfiguration gespeichert
  - Farbige Punkte mit Beschreibungstooltips

