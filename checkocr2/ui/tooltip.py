"""Tooltip widget for Tkinter."""

from __future__ import annotations

import tkinter as tk
from typing import Any

class ToolTip:
    """Create a tooltip for a given widget."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.id: str | None = None
        self.x = self.y = 0
        if hasattr(self.widget, "bind"):
            self.widget.bind("<Enter>", self.enter)
            self.widget.bind("<Leave>", self.leave)
            self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event: Any = None) -> None:
        self.schedule()

    def leave(self, event: Any = None) -> None:
        self.unschedule()
        self.hidetip()

    def schedule(self) -> None:
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self) -> None:
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def showtip(self) -> None:
        if self.tip_window or not self.text:
            return

        # Calculate tooltip position
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            foreground="#000000",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9)
        )
        label.pack(ipadx=3, ipady=1)

    def hidetip(self) -> None:
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()
