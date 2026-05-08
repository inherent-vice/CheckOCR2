"""Timing panel construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from typing import Protocol


class ThemeManagerLike(Protocol):
    def register_widget(self, widget: object, style_config: dict[str, object]) -> None:
        ...


class TimingPanelHost(Protocol):
    theme_manager: ThemeManagerLike
    paste_delay: object
    loading_delay: object

    def _create_section_frame_styled(
        self,
        parent: object,
        title: str,
        fill_parent: bool = False,
    ) -> object:
        ...


def create_timing_panel(app: TimingPanelHost, parent: object) -> None:
    section = app._create_section_frame_styled(parent, "⏱️ 타이밍 설정")
    common_font = ("Segoe UI", 9)

    timing_grid = tk.Frame(section)
    app.theme_manager.register_widget(timing_grid, {"bg": "white"})
    timing_grid.pack(fill="x")

    left_timing = tk.Frame(timing_grid)
    app.theme_manager.register_widget(left_timing, {"bg": "white"})
    left_timing.pack(side="left", fill="x", expand=True, padx=(0, 5))

    paste_lbl = tk.Label(
        left_timing,
        text="붙여넣기 딜레이(초):",
        font=(common_font[0], common_font[1], "bold"),
    )
    app.theme_manager.register_widget(paste_lbl, {"bg": "white", "fg": "on_surface"})
    paste_lbl.pack(anchor="w", pady=(0, 2))

    paste_entry = tk.Entry(
        left_timing,
        textvariable=app.paste_delay,
        font=common_font,
        width=10,
        relief="solid",
        bd=1,
    )
    app.theme_manager.register_widget(paste_entry, {"bg": "white", "fg": "on_surface"})
    paste_entry.pack(fill="x")

    right_timing = tk.Frame(timing_grid)
    app.theme_manager.register_widget(right_timing, {"bg": "white"})
    right_timing.pack(side="left", fill="x", expand=True, padx=(5, 0))

    load_lbl = tk.Label(
        right_timing,
        text="로딩 딜레이(초):",
        font=(common_font[0], common_font[1], "bold"),
    )
    app.theme_manager.register_widget(load_lbl, {"bg": "white", "fg": "on_surface"})
    load_lbl.pack(anchor="w", pady=(0, 2))

    load_entry = tk.Entry(
        right_timing,
        textvariable=app.loading_delay,
        font=common_font,
        width=10,
        relief="solid",
        bd=1,
    )
    app.theme_manager.register_widget(load_entry, {"bg": "white", "fg": "on_surface"})
    load_entry.pack(fill="x")
