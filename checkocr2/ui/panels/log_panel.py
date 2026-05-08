"""Log panel construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Protocol


class ThemeManagerLike(Protocol):
    def register_widget(self, widget: object, style_config: dict[str, str]) -> None:
        ...


class LogPanelHost(Protocol):
    theme_manager: ThemeManagerLike

    def _create_section_frame_styled(
        self,
        parent: object,
        title: str,
        fill_parent: bool = False,
    ) -> object:
        ...


def create_log_panel(app: LogPanelHost, parent: object) -> tk.Text:
    log_section_frame = app._create_section_frame_styled(parent, "📊 상태 및 로그", fill_parent=True)

    log_text_frame = tk.Frame(log_section_frame)
    app.theme_manager.register_widget(log_text_frame, {"bg": "white"})
    log_text_frame.pack(fill="both", expand=True, pady=(0, 5))

    log_text_widget = tk.Text(
        log_text_frame,
        font=("Segoe UI", 9),
        relief="solid",
        bd=1,
        wrap="word",
        state="disabled",
        width=20,
    )
    app.theme_manager.register_widget(
        log_text_widget,
        {"bg": "white", "fg": "on_surface", "insertbackground": "on_surface"},
    )

    log_scroll = ttk.Scrollbar(
        log_text_frame,
        orient="vertical",
        command=log_text_widget.yview,
        style="TScrollbar",
    )
    log_text_widget.configure(yscrollcommand=log_scroll.set)

    log_text_widget.pack(side="left", fill="both", expand=True)
    log_scroll.pack(side="right", fill="y")
    return log_text_widget
