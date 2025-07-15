# strategy.py


_FILTER_CONFIG = {}


def set_filter_config(filters):
    global _FILTER_CONFIG
    _FILTER_CONFIG = filters or {}


def get_filter_config():
    return _FILTER_CONFIG


def execute_trading_strategy(settings, gui):
    msg = "📡 Starte Trading-Strategie…"
    print(msg)
    if hasattr(gui, "log_event"):
        gui.log_event(msg)

    strategy_mode = "live" if not settings.get("paper_mode", True) else "paper"

    try:
        if strategy_mode == "live":
            from realtime_runner import run_bot_live
            msg = "🚀 Modus: LIVE aktiviert" if not settings.get("paper_mode", True) else "🚀 Modus: SIMULATION"
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
