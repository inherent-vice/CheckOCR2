"""Tooltip component for providing hover hints on UI elements."""

import tkinter as tk


class ToolTip:
    """A tooltip that appears when hovering over a widget."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500) -> None:
        """Initialize the ToolTip."""
        self.widget = widget
        self.text = text
        self.delay = delay
        self.id = None
        self.tw = None

        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event: tk.Event | None = None) -> None:
        """Schedule the tooltip to appear."""
        self.schedule()

    def leave(self, event: tk.Event | None = None) -> None:
        """Unschedule and hide the tooltip."""
        self.unschedule()
        self.hide()

    def schedule(self) -> None:
        """Schedule the tooltip."""
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self) -> None:
        """Unschedule the tooltip."""
        timer_id = self.id
        self.id = None
        if timer_id:
            self.widget.after_cancel(timer_id)

    def show(self, event: tk.Event | None = None) -> None:
        """Show the tooltip window."""
        self.unschedule()

        # Calculate position using winfo_rootx, winfo_rooty, and winfo_height
        # because Tkinter Button widgets do not support the bbox method.
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        # Creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window frame
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9, "normal")
        )
        label.pack(ipadx=1)

    def hide(self) -> None:
        """Hide the tooltip window."""
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
