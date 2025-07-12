# EntryMaster_Tradingview

**EntryMaster_Tradingview** ist ein reiner Live‑Trading‑Bot für Bitcoin-Futures. Das Projekt kombiniert einen TradingView-basierten Indikator mit einem anpassbaren Risiko- und Positionsmanagement. Die Bedienung erfolgt über eine Tkinter-GUI, die alle wichtigen Einstellungen und den API-Status anzeigt.

## Funktionen

- **Andac Entry-Master** – Port des TradingView-Skripts zur Generierung von Long-/Short-Signalen.
- **Adaptive SL/TP** – der `AdaptiveSLManager` berechnet Stop-Loss und Take-Profit dynamisch anhand des ATR.
- **Auto Partial Close** und Verlustbegrenzung – über den `RiskManager` können Teilverkaäufe und Drawdown-Limits konfiguriert werden.
- **Mehrere Börsen** – Unterstützt MEXC, dYdX, BitMEX sowie optionale Platzhalter für Binance und Bybit.
- **Preisfeed & Systemüberwachung** – der `SystemMonitor` prüft API‑Erreichbarkeit und Marktdaten. Die Zuordnung der REST-Endpunkte geschieht in `data_provider.py`.
- **GUI mit Status-Panel** – Eingabefelder für API-Schlüssel, Filteroptionen und Risko-Features. Ein Neon-Panel signalisiert wichtige Zustände.

## Installation

1. Python 3.10 oder neuer installieren.
2. Abhängigkeiten installieren:
   ```bash
   pip install requests colorama ecdsa bech32
   ```
3. Repository klonen und in das Verzeichnis wechseln:
   ```bash
   git clone <repo>
   cd EntryMaster_Tradingview
   ```
4. (Optional) eigene Einstellungen in `tuning_config.json` hinterlegen.

## Start

Der Bot wird über `python main.py` gestartet. Unter Windows steht alternativ `start_bot.cmd` bereit. Beim Start prüft `exchange_manager.py` vorhandene API-Daten und aktiviert nur korrekt konfigurierte Börsen.

## Konfiguration

Standardwerte befinden sich in `config.py`:
```python
SETTINGS = {
    "symbol": "BTC_USDT",
    "interval": "1m",
    "starting_balance": 1000,
    "leverage": 20,
    "stop_loss_atr_multiplier": 0.5,
    "take_profit_atr_multiplier": 1.5,
    "use_session_filter": False,
    "trading_backend": "mexc",
    "multiplier": 20,
    "auto_multiplier": False,
    "capital": 1000,
    "dydx_api_url": "https://api.dydx.trade/v4",
    "version": "V10.4_Pro",
}
```
Einstellungen lassen sich über die GUI oder durch Bearbeiten der `tuning_config.json` anpassen.

### API-Schlüssel

Alle Zugangsdaten können als Umgebungsvariable oder über die GUI gesetzt werden. Wichtige Variablen sind u.a. `MEXC_API_KEY`, `MEXC_API_SECRET`, `DYDX_PRIVATE_KEY`, `BINANCE_API_KEY`, `BYBIT_API_KEY` usw. Wird keine Börse korrekt konfiguriert, bleibt der Bot im Pausemodus.

## GUI

Die Tkinter-Oberfläche zeigt Kapital, PnL und Statusleuchten für API und Datenfeed. Parameter wie Multiplikator, Kapital oder Zeitfilter lassen sich direkt ändern. Buttons bieten Start/Stopp, Notausstieg und das Speichern von Profilen.

Ausschnitt aus der GUI-Initialisierung:
```python
self.apc_enabled = tk.BooleanVar(value=False)
self.max_loss_enabled = tk.BooleanVar(value=True)
self._build_controls(self.main_frame)  # Startknöpfe und Aktionen
```

## Preisfeeds

`data_provider.py` definiert REST-Endpunkte je Exchange:
```python
PRICE_FEEDS = {
    "mexc":    {"url": "https://contract.mexc.com/api/v1/contract/ticker?symbol={symbol}"},
    "bitmex":  {"url": "https://www.bitmex.com/api/v1/instrument?symbol={symbol}"},
    "binance": {"url": "https://api.binance.com/api/v3/ticker/price?symbol={symbol}"},
    "bybit":   {"url": "https://api.bybit.com/v2/public/tickers?symbol={symbol}"},
    "okx":     {"url": "https://www.okx.com/api/v5/market/ticker?instId={symbol}"},
}
```
Bei fehlerhaften Symbolen oder Netzwerkproblemen werden entsprechende Meldungen im Log ausgegeben.

## Logging & Fehlermeldungen

Das Projekt nutzt `central_logger.setup_logging()` für Datei- und Konsolenlogs. Wiederholte Meldungen werden zusammengefasst. Der `SystemMonitor` liefert Warnungen, wenn API oder Datenfeed ausfallen, und pausiert den Bot automatisch.

## Lizenz

Im Repository ist keine Lizenzdatei enthalten.
