"""Coordinate and capture-area panel construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from typing import Protocol


class ThemeManagerLike(Protocol):
    def register_widget(self, widget: object, style_config: dict[str, object]) -> None:
        ...


class CoordinatesPanelHost(Protocol):
    theme_manager: ThemeManagerLike

    def _create_section_frame_styled(
        self,
        parent: object,
        title: str,
        fill_parent: bool = False,
    ) -> object:
        ...

    def relocate_clickpoint(self) -> None:
        ...

    def relocate_allarea(self) -> None:
        ...

    def relocate_datearea(self) -> None:
        ...

    def relocate_ratearea(self) -> None:
        ...

    def show_area_preview(self) -> None:
        ...


def create_coordinates_panel(app: CoordinatesPanelHost, parent: object) -> None:
    section = app._create_section_frame_styled(parent, "🎯 좌표 및 영역 설정")
    common_font = ("Segoe UI", 9)
    btn_font = ("Segoe UI", 9)
    btn_height = 1

    grid_container = tk.Frame(section)
    app.theme_manager.register_widget(grid_container, {"bg": "white"})
    grid_container.pack(fill="x", pady=(0, 5))

    grid_container.grid_columnconfigure(0, weight=1)
    grid_container.grid_columnconfigure(1, weight=1)

    buttons = [
        ("🎯 클릭 포인트", app.relocate_clickpoint, {"bg": "accent", "fg": "white", "activebackground": "dark"}, 0, 0, (0, 2), (0, 2)),
        ("🔍 전체 영역", app.relocate_allarea, {"bg": "primary", "fg": "white", "activebackground": "dark"}, 0, 1, (2, 0), (0, 2)),
        ("🔍 날짜 영역", app.relocate_datearea, {"bg": "success", "fg": "white", "activebackground": "dark"}, 1, 0, (0, 2), (2, 0)),
        ("🔍 금리 영역", app.relocate_ratearea, {"bg": "warning", "fg": "white", "activebackground": "dark"}, 1, 1, (2, 0), (2, 0)),
    ]
    for text, command, style, row, column, padx, pady in buttons:
        button = tk.Button(
            grid_container,
            text=text,
            command=command,
            font=btn_font,
            relief="flat",
            cursor="hand2",
            height=btn_height,
            pady=0,
        )
        app.theme_manager.register_widget(button, style)
        button.grid(row=row, column=column, sticky="nsew", padx=padx, pady=pady)

    preview_all_btn = tk.Button(
        section,
        text="🔍 전체 영역 미리보기",
        command=app.show_area_preview,
        font=(common_font[0], common_font[1], "bold"),
        relief="flat",
        cursor="hand2",
        pady=4,
    )
    app.theme_manager.register_widget(
        preview_all_btn,
        {"bg": "warning", "fg": "white", "activebackground": "dark"},
    )
    preview_all_btn.pack(fill="x", pady=(8, 0))
