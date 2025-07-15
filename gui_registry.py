# gui_registry.py
"""Registry utilities to track Tkinter widgets for export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

registered_elements: list[dict[str, Any]] = []


def register_element(widget: Any, name: str, var: Any | None = None, command: Callable | None = None) -> None:
    """Register a widget with optional variable and command."""
    registered_elements.append({
        "widget": widget,
        "name": name,
        "var": var,
        "command": command,
    })


def export_gui(path: str = "gui_export.json") -> None:
    """Export information about all registered widgets to JSON."""
    elements = []
    for item in registered_elements:
        widget = item.get("widget")
        name = item.get("name")
        var = item.get("var")
        command = item.get("command")
        value = None
        if var is not None:
            try:
                value = var.get()
            except Exception:
                value = None
        elements.append({
            "name": name,
            "type": type(widget).__name__ if widget is not None else None,
            "has_logic": command is not None,
            "value": value,
        })

    Path(path).write_text(json.dumps(elements, indent=2, ensure_ascii=False), encoding="utf-8")

