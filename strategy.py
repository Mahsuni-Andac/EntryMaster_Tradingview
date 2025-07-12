# strategy.py


def execute_trading_strategy(settings, gui):
    """Starte die Trading-Strategie im Live-Modus."""
    msg = "📡 Starte Trading-Strategie…"
    print(msg)
    if hasattr(gui, "log_event"):
        gui.log_event(msg)

    strategy_mode = settings.get("strategy_mode", "live")

    try:
        if strategy_mode == "live":
            from realtime_runner import run_bot_live
            msg = "🚀 Modus: LIVE aktiviert"
            print(msg)
            if hasattr(gui, "log_event"):
                gui.log_event(msg)
            run_bot_live(settings, gui)
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
