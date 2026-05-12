"""Window-level actions for the legacy Tk shell."""

from __future__ import annotations

from typing import Any


def build_centered_geometry(
    *,
    screen_width: int,
    screen_height: int,
    window_width: int,
    window_height: int,
) -> str:
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    return f"{window_width}x{window_height}+{x}+{y}"


def center_window(app: Any) -> None:
    app.update_idletasks()
    app.geometry(
        build_centered_geometry(
            screen_width=app.winfo_screenwidth(),
            screen_height=app.winfo_screenheight(),
            window_width=app.winfo_width(),
            window_height=app.winfo_height(),
        )
    )
