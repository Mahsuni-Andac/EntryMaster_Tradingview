import tkinter as tk

NEON_COLORS = {
    "yellow": "#ffff33",
    "green": "#00ff00",
    "blue": "#00d0ff",
    "red": "#ff0033",
    "orange": "#ff9900",
}

class Tooltip:
    def __init__(self, widget, text=""):
        self.widget = widget
        self.text = text
        self.tipwindow = None

    def show(self, x, y):
        if self.tipwindow or not self.text:
            return
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{int(x)}+{int(y)}")
        label = tk.Label(tw, text=self.text, background="#222", foreground="white",
                         relief="solid", borderwidth=1, padx=4, pady=2)
        label.pack()

    def hide(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class NeonStatusPanel:
    """Panel with neon status bulbs."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent)
        bg = parent.cget("bg") if isinstance(parent, tk.Widget) else None
        self.canvas = tk.Canvas(self.frame, width=30, bg=bg, highlightthickness=0)
        self.canvas.pack(fill="y", expand=False)
        self.items = {}
        self.tooltip = Tooltip(self.canvas)

    def register(self, key: str, description: str):
        index = len(self.items)
        y = 10 + index * 30
        item = self.canvas.create_oval(5, y, 25, y + 20, fill=NEON_COLORS["yellow"], outline="")
        self.items[key] = {"item": item, "desc": description}
        self.canvas.tag_bind(item, "<Enter>", lambda e, k=key: self._on_enter(e, k))
        self.canvas.tag_bind(item, "<Leave>", lambda e: self._on_leave())

    def set_status(self, key: str, color: str, desc: str | None = None):
        if key not in self.items:
            return
        item = self.items[key]["item"]
        self.canvas.itemconfigure(item, fill=NEON_COLORS.get(color, color))
        if desc is not None:
            self.items[key]["desc"] = desc

    # ------------------------------------------------------------------
    def _on_enter(self, event, key):
        bbox = self.canvas.bbox(self.items[key]["item"])
        x = self.canvas.winfo_rootx() + bbox[2] + 5
        y = self.canvas.winfo_rooty() + bbox[1]
        self.tooltip.text = self.items[key]["desc"]
        self.tooltip.show(x, y)

    def _on_leave(self, event=None):
        self.tooltip.hide()
