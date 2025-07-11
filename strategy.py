# strategy.py

def execute_trading_strategy(settings, gui):
    """
    Startet die Trading-Strategie (LIVE oder SIM), basierend auf settings['strategy_mode'].
    - Bei Fehlern: Ausgabe im Terminal und ggf. GUI-Log.
    """
    msg = "📡 Starte Trading-Strategie…"
    print(msg)
    if hasattr(gui, "log_event"):
        gui.log_event(msg)

    strategy_mode = settings.get("strategy_mode")
    if not strategy_mode:
        strategy_mode = "sim" if settings.get("test_mode", False) else "live"

    try:
        if strategy_mode == "live":
            from realtime_runner import run_bot_live
            msg = "🚀 Modus: LIVE aktiviert"
            print(msg)
            if hasattr(gui, "log_event"):
                gui.log_event(msg)
            run_bot_live(settings, gui)

        elif strategy_mode == "sim":
            from realtime_runner import run_simulated_bot
            msg = "🧪 Modus: SIMULATION aktiviert"
            print(msg)
            if hasattr(gui, "log_event"):
                gui.log_event(msg)
            run_simulated_bot(settings, gui)

        else:
            msg = f"❓ Unbekannter Modus: '{strategy_mode}' – Abbruch"
            print(msg)
            if hasattr(gui, "log_event"):
                gui.log_event(msg)

    except ImportError as e:
        msg = f"❌ Import-Fehler bei Strategie-Komponenten: {type(e).__name__}: {e}"
        print(msg)
        if hasattr(gui, "log_event"):
            gui.log_event(msg)
    except Exception as e:
        msg = f"❌ Fehler beim Ausführen der Strategie: {type(e).__name__}: {e}"
        print(msg)
        if hasattr(gui, "log_event"):
            gui.log_event(msg)
