# EntryMaster_Tradingview

**EntryMaster_Tradingview** ist ein professioneller, aber einsteigerfreundlicher Bitcoin-Bot mit intelligenter Entry-Logik, risikoadaptivem Management und moderner, übersichtlicher GUI.  
Entwickelt für Einsteiger und Profis, die Live-Trading einfach und transparent steuern möchten.

---

## 🚀 **Features**

- **Andac Entry-Master Indikator**
  Alle Handelssignale basieren auf dem portierten TradingView-Skript.
- **Risikomanagement:**  
  - Dynamisches Stop-Loss/Take-Profit (ATR-basiert)
  - Maximalverlust pro Trade/Kapital-Schutz
- **Modular und erweiterbar:**  
  Saubere Trennung von Logik, Daten und GUI – einfach neue Strategien/Filter hinzufügen.

---

## 🖥️ **Grafische Oberfläche (GUI)**

- **Technik:**  
  Die GUI basiert auf [Tkinter](https://docs.python.org/3/library/tkinter.html) (keine Zusatzinstallation nötig).
- **Elemente:**
  - Live-Status (Balance, PnL)
  - Steuerung von Trading-Parametern (Symbol, Intervall, Multiplikator, Kapital)
  - Start/Stopp-Button für den Bot
  - Übersicht über Positionen und Log
  - Wirksamkeits-Status aller Einstellungen (✅/❌) – Änderungen werden sofort geprüft
- **Konfigurierbar:**  
  Fast alle Einstellungen können über die GUI angepasst und als **Profil gespeichert** werden.

---

## ⚡ **Schnellstart**

1. **Repository klonen:**
   ```bash
   git clone <dein-repo-link>
   cd EntryMaster_Tradingview


## dYdX Konfiguration

Um dYdX als dezentrale Perpetuals-Börse zu aktivieren, kann ein Private Key über die Umgebungsvariable `DYDX_PRIVATE_KEY` oder innerhalb der `SETTINGS` als `dydx_private_key` hinterlegt werden. Fehlt diese Angabe, bleibt der Adapter deaktiviert.

Der genutzte REST-Endpunkt lässt sich über `DYDX_API_URL` oder `dydx_api_url` anpassen. Standard ist `https://api.dydx.trade/v4`.

Beispiel `.env` Datei:
```env
DYDX_PRIVATE_KEY=mysecretkey
```

Alternativ in der `tuning_config.json`:
```json
{"dydx_private_key": "mysecretkey"}
```

Der Private Key wird nun beim Speichern genutzt, um die passende
`dydx1...`-Adresse lokal zu berechnen. Nur wenn Adresse und Key zusammenpassen
wird die Konfiguration übernommen.

### Automatische Exchange-Erkennung

Beim Start prüft der Bot, welche Zugangsdaten vorhanden sind. Nur vollständig konfigurierte Börsen werden aktiviert. Im Log erscheint eine Übersicht der aktiven Exchanges.

Unterstützte Umgebungsvariablen:

- `MEXC_API_KEY` / `MEXC_API_SECRET`
- `DYDX_PRIVATE_KEY`
- `DYDX_API_URL`
- `BINANCE_API_KEY` / `BINANCE_API_SECRET`
- `BYBIT_API_KEY` / `BYBIT_API_SECRET`

Alternativ können die gleichen Werte im `tuning_config.json` hinterlegt werden (`mexc_key`, `mexc_secret`, ...).

### Dynamische API-Eingabe in der GUI

In der GUI kann die gewünschte Börse ausgewählt werden. Je nach Auswahl erscheinen passende Felder (API Key/Secret oder Wallet/Private Key). Eingaben werden live validiert und nur im Arbeitsspeicher gespeichert. Beim Programmstart ist keine Exchange aktiv; Marktdaten werden aber bereits im Hintergrund geladen. Erst nach einer Auswahl werden die Zugangsdaten geprüft und der Status angezeigt.

Nach dem Speichern prüft der Bot die gewählte Exchange und zeigt das Ergebnis mit Zeitstempel im Log an, z.B.:

```
[12:00:00] ✅ MEXC API OK – Live-Marktdaten werden empfangen
[12:00:00] Aktive Exchanges: MEXC
[12:00:00] Live-Marktdaten aktiv: ✅
```

Ohne gültige Zugangsdaten läuft der Bot nicht. Ein Simulations- oder Backtest-Modus ist nicht vorhanden – es werden ausschließlich Live-Marktdaten verwendet.

### Preisfeeds & Endpunkte

Für jede unterstützte Börse wird ein eigener Preisfeed-Endpunkt genutzt. Die eigentlichen
Liveness-Checks erfolgen ausschließlich über einfache `/ping`- oder Zeit-Endpunkte.
So bleiben Verbindungsprüfung und Marktdaten klar getrennt.

| Exchange | Ping-Endpunkt | Preisfeed | Beispiel-Symbol |
|---------|---------------|-----------|-----------------|
| MEXC | `https://api.mexc.com/api/v3/ping` | `https://contract.mexc.com/api/v1/contract/ticker?symbol=BTC_USDT` | `BTC_USDT` |
| BitMEX | `https://www.bitmex.com/api/v1/instrument` | `https://www.bitmex.com/api/v1/instrument?symbol=XBTUSD` | `XBTUSD` |
| Binance | `https://api.binance.com/api/v3/ping` | `https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT` | `BTCUSDT` |
| Bybit | `https://api.bybit.com/v2/public/time` | `https://api.bybit.com/v2/public/tickers?symbol=BTCUSDT` | `BTCUSDT` |
| OKX | `https://www.okx.com/api/v5/public/time` | `https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP` | `BTC-USDT-SWAP` |

Fehlerhafte Symbole oder API-Antworten werden im Debug-Modus vollständig geloggt, damit
Probleme schnell erkannt werden können.
