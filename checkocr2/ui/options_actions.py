"""Options-panel actions for the legacy Tk shell."""

from __future__ import annotations

from typing import Any


def toggle_upscaling_details(app: Any) -> None:
    if hasattr(app, "upscaling_details_frame"):
        children = app.upscaling_details_frame.winfo_children()
        if app.enable_upscaling.get():
            for child in children:
                child.pack_configure()
        else:
            for child in children:
                child.pack_forget()

    app.save_advanced_ui_to_settings()
