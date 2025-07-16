def execute_trading_strategy(settings, gui):
    msg = "📡 Starte Trading-Strategie…"
    print(msg)
    if hasattr(gui, "log_event"):
        gui.log_event(msg)

    strategy_mode = "live" if not settings.get("paper_mode", True) else "paper"

    try:
        if strategy_mode == "live":
            from realtime_runner import run_bot_live
            msg = "🚀 LIVE-Modus aktiviert"
            print(msg)
            gui.log_event(msg) if hasattr(gui, "log_event") else None
            run_bot_live(settings, gui)
        else:
            from simulator import run_bot_simulation
            msg = "🧪 Paper-Trading-Modus aktiviert"
            print(msg)
            gui.log_event(msg) if hasattr(gui, "log_event") else None
            run_bot_simulation(settings, gui)
    except ImportError as e:
        msg = f"❌ Import-Fehler: {type(e).__name__}: {e}"
        print(msg)
        gui.log_event(msg) if hasattr(gui, "log_event") else None
    except Exception as e:
        msg = f"❌ Laufzeitfehler: {type(e).__name__}: {e}"
        print(msg)
        gui.log_event(msg) if hasattr(gui, "log_event") else None
