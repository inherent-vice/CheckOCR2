"""Section frame construction for the legacy Tk shell."""

from __future__ import annotations

import tkinter as tk
from typing import Protocol


class ThemeManagerLike(Protocol):
    def register_widget(
        self, widget: object, style_config: dict[str, object]
    ) -> None: ...


class SectionFrameHost(Protocol):
    theme_manager: ThemeManagerLike


def create_section_frame_styled(
    app: SectionFrameHost,
    parent: tk.Misc | None,
    title: str,
    *,
    fill_parent: bool = False,
) -> tk.Frame:
    frame = tk.Frame(parent)
    app.theme_manager.register_widget(
        frame,
        {"bg": "surface", "relief": "groove", "bd": 1, "padx": 3, "pady": 3},
    )

    if fill_parent:
        frame.pack(fill="both", expand=True, padx=3, pady=3)
    else:
        frame.pack(fill="x", padx=3, pady=3)

    title_lbl = tk.Label(
        frame,
        text=title,
        anchor="w",
        font=("Segoe UI", 10, "bold"),
    )
    app.theme_manager.register_widget(title_lbl, {"bg": "surface", "fg": "primary"})
    title_lbl.pack(fill="x", pady=(0, 5))

    content_frame = tk.Frame(frame)
    app.theme_manager.register_widget(
        content_frame,
        {"bg": "white", "padx": 3, "pady": 3, "relief": "solid", "bd": 1},
    )
    content_frame.pack(fill="both", expand=True)

    return content_frame
