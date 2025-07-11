# filter_recommender.py

def update_filter_recommendations(app, candle):
    try:
        close = candle.get("close", 0)
        high = candle.get("high", 0)
        low = candle.get("low", 0)
        open_ = candle.get("open", 0)
        volume = candle.get("volume", 0)

        # 🔎 RSI-Zone
        midpoint = (high + low) / 2
        range_ = high - low if high - low != 0 else 1
        relative = (close - midpoint) / range_
        rsi = 50 + (relative * 50)
        rsi = max(0, min(100, rsi))

        if rsi < 30:
            app.rsi_min.set("20")
            app.rsi_max.set("60")
            app.rsi_rec_label.config(text="20–60")
        elif rsi > 70:
            app.rsi_min.set("40")
            app.rsi_max.set("90")
            app.rsi_rec_label.config(text="40–90")
        else:
            app.rsi_min.set("35")
            app.rsi_max.set("75")
            app.rsi_rec_label.config(text="35–75")

        # ✅ RSI-Haken setzen
        app.rsi_chk_rec.config(text="✅")

        # 🔎 Volumenfilter
        if volume > 1000:
            app.min_volume.set("900")
            app.volume_rec_label.config(text="900")
        else:
            app.min_volume.set("600")
            app.volume_rec_label.config(text="600")

        app.volume_chk_rec.config(text="✅")

        # 🔎 Volumen-Boost
        app.volume_avg_period.set("13")
        app.volboost_rec_label.config(text="13")
        app.volboost_chk_rec.config(text="✅")

        # 🔎 EMA-Länge anpassen
        app.ema_length.set("22")
        app.ema_rec_label.config(text="22")
        app.ema_chk_rec.config(text="✅")

        # 🔎 SL/TP-Modus & Mindestabstand
        app.sl_mode.set("atr")
        app.slmode_rec_label.config(text="ATR")
        app.sl_tp_min_distance.set("4.3")
        app.slmin_rec_label.config(text="4.3")

        # 🔎 Score-Schwelle
        app.entry_score_threshold.set("0.7")
        app.score_rec_label.config(text="0.7")

        # 🔎 Struktur-Filter
        app.bigcandle_threshold.set("1.6")
        app.breakout_lookback.set("12")
        app.bigcandle_rec_label.config(text="1.6")
        app.breakout_rec_label.config(text="12")

        # ✅ Alle Checkbox-Empfehlungen setzen
        app.engulf_chk_rec.config(text="✅")
        app.bigcandle_chk_rec.config(text="✅")
        app.breakout_chk_rec.config(text="✅")
        app.doji_chk_rec.config(text="✅")
        app.ema_chk_rec.config(text="✅")
        app.cool_chk_rec.config(text="✅")
        app.safe_chk_rec.config(text="✅")
        app.smartcool_chk_rec = app.cool_chk_rec  # Fallback alias für alte Namen

    except Exception as e:
        print(f"⚠️ Fehler bei Filter-Empfehlung: {e}")
