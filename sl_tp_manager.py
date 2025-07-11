# sl_tp_manager.py
def calculate_sl_tp(self, direction, entry, candle, ctx=None, multiplier=20, rr_ratio=1.8, atr_multiplier=2.2):
    """
    Berechnet Stop-Loss und Take-Profit basierend auf ATR, Multiplikator und Risk-Reward.
    Kontext-Parameter können aus ctx (z.B. Namespace, dict) überschrieben werden.
    """
    # ATR berechnen, Mindestschwelle setzen
    atr = self.calculate_atr(candle)
    atr = max(atr, 10)

    # Aus Kontext überschreiben, falls gesetzt
    if ctx:
        rr_ratio = getattr(ctx, 'rr_ratio', rr_ratio)
        atr_multiplier = getattr(ctx, 'atr_multiplier', atr_multiplier)
        multiplier = getattr(ctx, 'multiplier', multiplier)

    sl_dist = atr * atr_multiplier * (multiplier / 20)  # Normiert auf Standardhebel 20
    tp_dist = sl_dist * rr_ratio

    if direction == "long":
        sl = round(entry - sl_dist, 2)
        tp = round(entry + tp_dist, 2)
    elif direction == "short":
        sl = round(entry + sl_dist, 2)
        tp = round(entry - tp_dist, 2)
    else:
        raise ValueError("Unknown direction for SL/TP.")

    return sl, tp
