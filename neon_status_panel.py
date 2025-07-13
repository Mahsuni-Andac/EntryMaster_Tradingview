# neon_status_panel.py
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

    BULB_SIZE = 20
    PADDING = 10

    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent)
        bg = parent.cget("bg") if isinstance(parent, tk.Widget) else None
        self.canvas = tk.Canvas(
            self.frame, width=30, bg=bg, highlightthickness=0
        )
        self.canvas.pack(fill="y", expand=False)

        self.items: dict[str, dict] = {}
        self.tooltip = Tooltip(self.canvas)
        self.max_rows = 0
        self.canvas.bind("<Configure>", lambda e: self._layout())
        self.frame.bind("<Configure>", lambda e: self._layout())

    def register(self, key: str, description: str):
        self.items[key] = {"item": None, "desc": description, "color": "yellow"}
        self._layout()

    def set_status(self, key: str, color: str, desc: str | None = None):
        if key not in self.items:
            return
        info = self.items[key]
        info["color"] = color
        if desc is not None:
            info["desc"] = desc
        if info["item"] is not None:
            self.canvas.itemconfigure(
                info["item"], fill=NEON_COLORS.get(color, color)
            )

    def _layout(self):
        if not self.items:
            return
        height = self.frame.winfo_height()
        if height <= 1:
            self.frame.after(50, self._layout)
            return

        max_rows = max(1, height // (self.BULB_SIZE + self.PADDING))
        if max_rows != self.max_rows:
            self.max_rows = max_rows

        cols = (len(self.items) + max_rows - 1) // max_rows
        self.canvas.config(width=30 * cols, height=height)
        self.canvas.delete("all")

        for index, (key, info) in enumerate(self.items.items()):
            col = index // max_rows
            row = index % max_rows
            x = 5 + col * 30
            y = 10 + row * (self.BULB_SIZE + self.PADDING)
            item = self.canvas.create_oval(
                x,
                y,
                x + self.BULB_SIZE,
                y + self.BULB_SIZE,
                fill=NEON_COLORS.get(info["color"], info["color"]),
                outline="",
            )
            info["item"] = item
            self.canvas.tag_bind(item, "<Enter>", lambda e, k=key: self._on_enter(e, k))
            self.canvas.tag_bind(item, "<Leave>", self._on_leave)

    def _on_enter(self, event, key):
        bbox = self.canvas.bbox(self.items[key]["item"])
        x = self.canvas.winfo_rootx() + bbox[2] + 5
        y = self.canvas.winfo_rooty() + bbox[1]
        self.tooltip.text = self.items[key]["desc"]
        self.tooltip.show(x, y)

    def _on_leave(self, event=None):
        self.tooltip.hide()
