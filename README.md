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
hinterlegt sind. Dort lässt sich auch die Option `data_source_mode` setzen:

- `websocket` – nutze ausschließlich den Binance WebSocket
- `rest` – nutze ausschließlich REST-Requests
- `auto` – versuche WebSocket und falle automatisch auf REST zurück, wenn keine Verbindung zustande kommt


## Starten
```bash
python main.py
```
Die GUI fragt die BitMEX-Zugangsdaten ab und zeigt fortlaufend die Binance-Spot-
Preise sowie die Entwicklung des Paper-Trading-Kontos an. Über einen Schalter kann jederzeit vom Simulationsmodus in den Live-Betrieb gewechselt werden.

## 📡 Datenquelle

Der EntryMaster Bot nutzt WebSocket-Preisdaten von Binance BTCUSDT. Bei Fehler erfolgt ein automatischer Fallback auf REST. Die Quelle wird live in der GUI angezeigt. Die WebSocket-Verbindung ist stabil, einmalig und kollisionsfrei mit der Tkinter-Oberfläche integriert.

Der Bot kann Binance-Marktdaten über einen WebSocket-Stream oder per REST-API beziehen.
In der GUI lässt sich der Modus zwischen **WebSocket**, **REST** und **Auto** auswählen.
Im Auto-Modus wird zuerst versucht, einen WebSocket aufzubauen. Schlägt das fehl oder bricht die Verbindung ab, stellt der Bot automatisch auf REST um. Läuft der WebSocket bereits, wird er nicht erneut gestartet. Beim Wechsel des Datenmodus wird ein vorhandener Stream vorher mit `twm.stop()` beendet. Der aktuell genutzte Modus wird in der GUI angezeigt:

Der WebSocket wird nur einmal gestartet und bleibt aktiv, bis der Modus geändert wird. Beim Wechsel des Datenmodus werden laufende Streams sauber beendet, damit keine doppelten Verbindungen entstehen.

- **🟢 WebSocket aktiv** – Stream aktiv
- **🔴 REST aktiv** – Fallback auf REST

## Live-Daten-Handling

### 📡 Datenquellen (Binance BTCUSDT)
- Der Bot unterstützt **zwei Datenquellen** für Marktdaten:
  - WebSocket (schnell, zuverlässig, ohne Auth)
  - REST-API (Fallback bei Verbindungsproblemen)

- Über die GUI kann per Schalter umgeschaltet werden zwischen:
  - `Auto` (empfohlen): bevorzugt WebSocket, wechselt bei Problemen zu REST
  - `WebSocket`: nutzt ausschließlich Live-Stream
  - `REST`: nutzt zyklischen Abruf alle 1s

- Die aktive Datenquelle wird in der GUI angezeigt. Konflikte werden intern gelöst. **Es ist immer nur eine Datenquelle gleichzeitig aktiv.**

### 📡 Datenquelle: Binance BTCUSDT (Spot)
Der EntryMaster-Bot nutzt immer BTCUSDT-Marktdaten von Binance Spot (nicht Futures). Der Preisfeed erfolgt standardmäßig über WebSocket für Echtzeit-Ticks. Sollte dieser ausfallen, greift der Bot automatisch auf REST zurück. Der Benutzer kann im GUI-Feld bei der API-Konfiguration manuell auswählen:

- **Auto** → versucht WebSocket, fällt zurück auf REST
- **WebSocket** → erzwingt Echtzeit-Ticks
- **REST** → fallback-only (z. B. bei Netzrestriktionen)

Wichtig: Der Preisfeed wird niemals über andere Börsen gespeist. BitMEX dient nur zur Orderausführung bei Live-Trading.

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

