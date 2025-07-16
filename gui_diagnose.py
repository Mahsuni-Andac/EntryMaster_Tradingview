import tkinter as tk
from tkinter import ttk
from datetime import datetime


def _widget_info(widget: tk.Widget) -> dict:
    name = ''
    if 'text' in widget.keys():
        name = widget.cget('text')
    if not name:
        name = getattr(widget, '_name', widget.winfo_class())
    value = ''
    try:
        if isinstance(widget, (tk.Entry, ttk.Entry)):
            value = widget.get()
        elif isinstance(widget, tk.Text):
            value = widget.get('1.0', 'end').strip()
        elif isinstance(widget, ttk.Combobox):
            value = widget.get()
        elif 'text' in widget.keys():
            value = widget.cget('text')
    except Exception:
        value = ''
    visible = bool(widget.winfo_ismapped())
    has_logic = False
    try:
        if 'command' in widget.keys() and widget.cget('command'):
            has_logic = True
    except Exception:
        pass

    hints: list[str] = []
    if isinstance(widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)) and value == '':
        hints.append('kein Wert gesetzt')
    if isinstance(widget, (tk.Checkbutton, ttk.Checkbutton)) and not widget.cget('variable'):
        hints.append('keine Variable verbunden')
    if isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox)) and 'textvariable' in widget.keys() and not widget.cget('textvariable'):
        hints.append('keine Variable verbunden')

    return {
        'name': name,
        'type': widget.winfo_class(),
        'value': value,
        'visible': visible,
        'has_logic': has_logic,
        'hints': hints,
    }


def generate_diagnose_md(root: tk.Widget, filename: str = 'gui_diagnose.md') -> None:
    report: list[str] = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report.append('# GUI Diagnose')
    report.append('')
    report.append('Automatisch erzeugter Bericht der Trading-GUI.')
    report.append(f'_Erstellt am {timestamp}_')
    report.append('')

    stats = {'total': 0, 'no_logic': 0, 'empty': 0}

    def walk(widget: tk.Widget, section: str | None = None):
        for child in widget.winfo_children():
            if isinstance(child, ttk.Notebook):
                for tab_id in child.tabs():
                    frame = child.nametowidget(tab_id)
                    title = child.tab(tab_id, 'text') or frame.winfo_name()
                    report.append(f'## Abschnitt: {title}')
                    walk(frame, title)
            elif isinstance(child, (tk.LabelFrame, ttk.LabelFrame)):
                title = child.cget('text') or child.winfo_name()
                report.append(f'## Abschnitt: {title}')
                walk(child, title)
            elif isinstance(child, (tk.Frame, ttk.Frame)):
                walk(child, section)
            else:
                info = _widget_info(child)
                stats['total'] += 1
                if not info['has_logic']:
                    stats['no_logic'] += 1
                if isinstance(child, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)) and info['value'] == '':
                    stats['empty'] += 1
                report.append(f"### Widget: {info['name']}")
                report.append(f"- Typ: {info['type']}")
                report.append(f"- Standardwert: {info['value']}")
                report.append(f"- Sichtbar: {'Ja' if info['visible'] else 'Nein'}")
                report.append(f"- Logik: {'Ja' if info['has_logic'] else 'Nein'}")
                if info['hints']:
                    report.append('- Hinweise:')
                    for h in info['hints']:
                        report.append(f'  - {h}')
                report.append('')

    walk(root)

    report.append('---')
    report.append('## Zusammenfassung')
    report.append(f"- Anzahl aller Widgets: {stats['total']}")
    report.append(f"- Anzahl ohne Logik: {stats['no_logic']}")
    report.append(f"- Anzahl leerer Felder: {stats['empty']}")

    with open(filename, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(report))


def add_gui_diagnose_button(root: tk.Widget) -> None:
    btn = tk.Button(root, text='📋 GUI-Diagnose (Markdown)', command=lambda: generate_diagnose_md(root))
    btn.grid(row=999, column=0, columnspan=2, pady=10)

