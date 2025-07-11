# trading_gui_score_display.py

import tkinter as tk
from tkinter import ttk

class ScoreDisplay(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self._build_widgets()

    def _build_widgets(self):
        self.score_label = tk.Label(self, text="Score: 0.00", font=("Arial", 10))
        self.score_label.grid(row=0, column=0, sticky="w", padx=2)

        self.score_bar = ttk.Progressbar(self, length=160, maximum=1.0)
        self.score_bar.grid(row=1, column=0, sticky="w", pady=(2, 0), padx=2)

        self.detail_label = tk.Label(self, text="", font=("Arial", 9), fg="gray")
        self.detail_label.grid(row=2, column=0, sticky="w", padx=2)

        self.signal_status = tk.Label(self, text="⏳ Kein Signal", font=("Arial", 8), fg="gray")
        self.signal_status.grid(row=3, column=0, sticky="w", pady=(2, 0), padx=2)

    def update_score(self, score: float, details: str = "", signal_text: str = None):
        """Aktualisiert Score-Balken und Text (0-1 Skala empfohlen)."""
        try:
            score = max(0.0, min(1.0, float(score)))
        except:
            score = 0.0
        self.score_label.config(text=f"Score: {score:.2f}")
        self.score_bar['value'] = score
        self.detail_label.config(text=details if details else "")
        if signal_text is not None:
            self.signal_status.config(text=signal_text)
        # Optional: Farbe der Leiste nach Score ändern
        if score >= 0.8:
            self.score_bar.configure(style='green.Horizontal.TProgressbar')
        elif score >= 0.6:
            self.score_bar.configure(style='yellow.Horizontal.TProgressbar')
        else:
            self.score_bar.configure(style='red.Horizontal.TProgressbar')

def setup_score_bar_styles(root):
    """Ruft das im Hauptfenster auf, um die Score-Farben zu ermöglichen."""
    style = ttk.Style(root)
    style.theme_use("default")
    style.configure("green.Horizontal.TProgressbar", troughcolor="#e0ffe0", background="#47cc47")
    style.configure("yellow.Horizontal.TProgressbar", troughcolor="#ffffe0", background="#e6d94d")
    style.configure("red.Horizontal.TProgressbar", troughcolor="#ffeaea", background="#e05252")

