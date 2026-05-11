"""Log text widget actions for the legacy Tk shell."""

from __future__ import annotations

import tkinter as tk
from typing import Any


def append_log_text(app: Any, message: str, level_name: str = "INFO") -> None:
    log_widget = getattr(app, "log_text_widget", None)
    if not log_widget or not log_widget.winfo_exists():
        return

    log_widget.config(state="normal")
    tag = level_name.upper()
    if tag not in log_widget.tag_names():
        tag = "INFO"
    log_widget.insert(tk.END, f"{message}\n", tag)
    log_widget.see(tk.END)
    log_widget.config(state="disabled")
