import tkinter as tk
from tkinter import ttk
import os
from datetime import datetime


def describe_widget(widget):
    lines = []
    try:
        name = widget._name
        widget_type = widget.winfo_class()
        visible = widget.winfo_ismapped()
        has_logic = False
        value = None
        issues = []
        actions = []

        try:
            if hasattr(widget, 'cget') and widget.cget('command'):
                has_logic = True
        except Exception:
            pass

        try:
            if isinstance(widget, tk.Entry):
                value = widget.get()
                if value.strip() == "":
                    issues.append("Feld ist leer.")
                    actions.append("Feld sollte vorbelegt oder validiert werden.")
            elif isinstance(widget, tk.Checkbutton):
                value = widget.var.get() if hasattr(widget, 'var') else None
                if value is None:
                    issues.append("Keine Variable verbunden.")
                    actions.append("`variable`-Objekt fehlt oder ist None.")
            elif isinstance(widget, tk.Label):
                value = widget.cget("text")
            elif isinstance(widget, tk.Scale):
                value = widget.get()
            elif isinstance(widget, tk.Text):
                value = widget.get("1.0", "end").strip()
            elif isinstance(widget, ttk.Combobox):
                value = widget.get()
        except Exception as e:
            issues.append(f"Fehler beim Lesen des Wertes: {str(e)}")

        lines.append(f"### 🧱 Widget: `{name}`\n")
        lines.append(f"- **Typ:** `{widget_type}`")
        lines.append(f"- **Sichtbar:** `{visible}`")
        lines.append(f"- **Wert:** `{value}`")
        lines.append(f"- **Logik vorhanden:** `{has_logic}`")

        if issues:
            lines.append(f"- ❗ **Probleme:**")
            for issue in issues:
                lines.append(f"  - {issue}")
        if actions:
            lines.append(f"- ✅ **Empfehlungen:**")
            for act in actions:
                lines.append(f"  - {act}")

        lines.append("")
    except Exception as e:
        lines.append(f"- Fehler bei Analyse eines Widgets: {str(e)}\n")

    return "\n".join(lines)


def scan_widgets_to_markdown(root, filename="gui_diagnose.md"):
    all_widgets = []

    def recurse(widget):
        all_widgets.append(widget)
        for child in widget.winfo_children():
            recurse(child)

    recurse(root)

    content = [f"# 🧩 GUI Diagnosebericht – {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"]
    content.append(f"**Anzahl Widgets insgesamt:** {len(all_widgets)}\n")

    logic_missing = 0
    issues_found = 0

    for w in all_widgets:
        desc = describe_widget(w)
        content.append(desc)
        if "- **Logik vorhanden:** `False`" in desc:
            logic_missing += 1
        if "❗" in desc:
            issues_found += 1

    content.append("---")
    content.append("## 📊 Zusammenfassung")
    content.append(f"- Gesamtzahl Widgets: **{len(all_widgets)}**")
    content.append(f"- Ohne Logik: **{logic_missing}**")
    content.append(f"- Mit erkannten Problemen: **{issues_found}**")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(content))

    print(f"📄 Diagnosebericht gespeichert: {filename}")


def add_gui_diagnose_button(root):
    btn = tk.Button(root, text="📋 GUI-Diagnose (Markdown)", command=lambda: scan_widgets_to_markdown(root))
    btn.grid(row=999, column=0, columnspan=2, pady=10)
