"""ToolTip component for providing hover hints on Tkinter widgets."""

from __future__ import annotations

import tkinter as tk


class ToolTip:
    """Creates a tooltip for a given Tkinter widget."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500) -> None:
        """
        Initialize the ToolTip.

        Args:
            widget: The widget to attach the tooltip to.
            text: The text to display in the tooltip.
            delay: Delay in milliseconds before showing the tooltip.
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.id: str | None = None
        self.tw: tk.Toplevel | None = None

        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event: tk.Event[tk.Widget] | None = None) -> None:
        """Schedule the tooltip to appear after a delay."""
        self.schedule()

    def leave(self, event: tk.Event[tk.Widget] | None = None) -> None:
        """Cancel scheduled tooltip and hide any visible tooltip."""
        self.unschedule()
        self.hidetip()

    def schedule(self) -> None:
        """Unschedule any existing timer and schedule a new one."""
        self.unschedule()
        self.id = self.widget.after(self.delay, self.showtip)

    def unschedule(self) -> None:
        """Cancel the scheduled tooltip timer."""
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def showtip(self) -> None:
        """Create and display the tooltip window."""
        if self.tw:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tw = tk.Toplevel(self.widget)
        # Removes the window decorations
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 8, "normal")
        )
        label.pack(ipadx=1)

    def hidetip(self) -> None:
        """Destroy the tooltip window."""
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
