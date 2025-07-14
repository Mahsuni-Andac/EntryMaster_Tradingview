# EntryMaster Trading Bot

**EntryMaster** ist ein professioneller BTC/USDT-Trading-Bot. Die Marktanalyse nutzt Candle-Daten der **Binance**-WebSocket, während sämtliche Orders ausschließlich über die **BitMEX REST-API** auf **XBTUSD** ausgeführt werden. Der Bot kombiniert eine leistungsstarke Entry-Strategie (Andac Entry Master) mit adaptivem Risiko-Management, einem benutzerfreundlichen GUI-Interface und einem vollständig simulierbaren Paper-Trading-Modus.

👉 **Nur eine Datenquelle:** Es gibt keinerlei REST-Fallback oder zweite WebSocket. Alle Marktdaten stammen ausschließlich von der Binance WebSocket, während BitMEX als einziger Broker genutzt wird.

Dieses Repository folgt drei Prinzipien:
- Alle Dateien liegen direkt im Hauptordner
- Jede Datei startet mit `# dateiname.py`
- Es existieren keine beschreibenden Kommentare

---

## 🚀 Funktionen im Überblick

- 📡 **Binance-WebSocket** liefert Kerzen zur Entscheidungsfindung (`wss://stream.binance.com`).
- 📄 **Orders ausschließlich über BitMEX REST** auf `XBTUSD`.
- ❌ Kein REST-Fallback oder zweite Datenquelle – Minimalismus pur.
- ⏱️ **1-Minuten-Candles** (`kline_1m`) für präzise Entry-/Exit-Entscheidungen.
- ✅ **Nur abgeschlossene Candles** (`kline['x'] == True`) werden verarbeitet.
- 📊 **Adaptive SL/TP-Logik**: auf Basis von ATR und Candle-Historie.
- 🛡️ **Drawdown-/Verlustbegrenzung** über einen integrierten `RiskManager`.
- 🧪 **Realistischer Paper-Trading-Modus** mit vollständiger PnL-Berechnung.
- 💼 **Live-Modus mit API-Keys** optional aktivierbar.
- 🎛️ **Modulare Konfiguration** über mehrere Tabs in der GUI.
- 🖥️ **Darkmode-GUI** auf Basis von Dash + Tkinter.
- 📈 **Realtime-Log**, Systemstatus, und Telegram-Alerts.
- 🔄 **Auto Partial Close (APC)**: Gewinnmitnahme nach konfigurierbarer PnL-Logik.
- ✍️ **Manuelle SL/TP-Eingabe** möglich mit Validierung und Statusanzeige.

---

## 🧠 Strategie: Andac Entry Master

Der Bot verwendet eine fortgeschrittene Entry-Strategie:

- ✅ **Trendfilter** (EMA)
- ✅ **Volumenstärke-Erkennung**
- ✅ **Makrophasen-Filter**
- ✅ **Session-Filter**
- ⚙️ **Session-Filter konfigurierbar über die GUI**
- ✅ **Engulfing-Pattern**
- ✅ **Multi-Timeframe-Bestätigung**
- 🟢 Alle Signale werden geloggt, mit Gründen bei Verwerfung.

---

## 🛡️ Risikomanagement

- 🔒 Adaptiver Stop-Loss / Take-Profit via `adaptive_sl_manager.py`.
- ❌ Kein Fallback – SL/TP müssen valide sein oder der Trade wird nicht ausgeführt.
- ✅ Live-Bestätigung über GUI (Grün-Schaltung nach Prüfung).
- 💰 Verlustgrenzen & Drawdown-Prozente via `risk_manager.py`.

---

## 📦 Installation

1. **Python 3.10 oder neuer installieren**
2. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🧾 Konfiguration

Die wichtigsten Einstellungen findest du in `config.py` und innerhalb der GUI.

- Standard-Symbol: `BTCUSDT`
- Standard-Modus: Paper Trading
- `data_source_mode` ist fix auf `websocket`
- API-Keys werden in der GUI gespeichert
- SL/TP ATR-Multiplikatoren einstellbar
- Auto Partial Close separat aktivierbar

---

## 🧪 Start im Paper-Modus

```bash
python main.py
```

- GUI öffnet sich automatisch.
- Paper-Konto startet mit $1.000 Kapital (einstellbar).
- Candle-Feed und Signale starten sofort.
- Alle Trades simuliert (kein echter Markt-Zugriff).
- Status: `✅ Marktdaten kommen an`

---

## 💼 Start im Live-Modus

1. API-Key + Secret in GUI eintragen
2. Toggle `LIVE TRADING` aktivieren
3. Die Statusanzeige wechselt auf LIVE
4. Trades werden nun real über BitMEX (XBTUSD) platziert

**Hinweis:** Market Orders werden via BitMEX REST-API ausgeführt.

---

## 🎛️ GUI-Komponenten

- 📊 Preisfeed: Echtzeit BTC/USDT Kursanzeige
- 🔄 SL/TP Steuerung:
  - Auto Partial Close (APC) mit Prozentregel
  - Manuelle SL/TP Eingabe über GUI + Validierungs-Button
- 📈 Trade-Log: Einträge mit Uhrzeit, Signal, Entry, Exit, PnL
- 🟢 Glühbirnen-Status für alle Systeme
- 🛠️ Systemzustand + Debug-Panel

---

## 🐞 Fehlererkennung & Statusüberwachung

- WebSocket-Feed wird überwacht
- Feed-Ausfall führt zu automatischer Pause
- Fehlende Daten (z. B. Volume, High) werden geloggt und ignoriert
- Systemstatus zeigt aktiv Probleme an

---

## ✅ Beispiel-Statusanzeige

```text
✅ Marktdaten kommen an | ✅ SL aktiv | ✅ TP aktiv | 🟢 Binance WebSocket OK
```

---

## 📤 Telegram Integration (optional)

- Konfigurierbare Push-Benachrichtigungen
- Aktivierbar über GUI-Tabs

---

## 📁 Projektstruktur

```text
EntryMaster_Tradingview/
├── adaptive_sl_manager.py
├── andac_entry_master.py
├── api_credential_frame.py
├── api_key_manager.py
├── auto_recommender.py
├── binance_ws.py
├── central_logger.py
├── config.py
├── console_status.py
├── cooldown_manager.py
├── data_provider.py
├── global_state.py
├── gui_bridge.py
├── indicator_utils.py
├── main.py
├── neon_status_panel.py
├── pnl_utils.py
├── realtime_runner.py
├── risk_manager.py
├── status_block.py
├── status_events.py
├── strategy.py
├── system_monitor.py
├── trading_gui_core.py
├── trading_gui_logic.py
├── test_api_key_manager.py
├── test_pnl_utils.py
├── test_system_monitor.py
└── requirements.txt
```

---

## Architekturprinzipien

🔹 **Maximale Reduktionsstrategie**: Jede Zeile Code erfüllt eine klar definierte Funktion. Keine ungenutzten Methoden, veralteten Imports oder toten Abhängigkeiten.
🔹 **Keine Redundanzen**: Nur eine zuständige Quelle pro Aufgabe (z. B. eine Candle-Quelle, ein Preis-Handler).
🔹 **Live-Stabilität vor Funktionserweiterung**: Der Code ist für Latenzfreiheit und Fehlertoleranz im Dauerbetrieb optimiert.
🔹 **Single Responsibility**: Jede Datei hat eine klar eingegrenzte Verantwortung (z. B. WebSocket, GUI, Strategy, Logging).

---

## ✨ Noch in Entwicklung (Roadmap)

- GUI-basierte Backtests
- Weitere Assets (nur BTCUSDT bisher)
- Session-Wizard zur Konfiguration
- Optimierte Logging-Ausgabe & Reports

---

## 📬 Kontakt & Mitwirken

Du möchtest mitentwickeln oder brauchst Hilfe? Schreib mir auf Telegram oder öffne ein Issue.
