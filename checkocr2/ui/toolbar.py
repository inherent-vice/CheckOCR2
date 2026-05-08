"""Toolbar construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Protocol


class ThemeManagerLike(Protocol):
    available_themes: dict[str, dict[str, str]]
    current_theme_key: str

    def register_widget(self, widget: object, style_config: dict[str, object]) -> None:
        ...

    def change_theme(self, theme_key: str) -> None:
        ...


class ToolbarHost(Protocol):
    theme_manager: ThemeManagerLike
    theme_var: object
    run_btn: object
    stop_btn: object
    theme_combo: object

    def run_ocr_process(self) -> None:
        ...

    def stop_processing_ui_initiated(self) -> None:
        ...


def create_simple_toolbar(app: ToolbarHost) -> None:
    toolbar = tk.Frame(app, height=35)
    app.theme_manager.register_widget(toolbar, {"bg": "primary"})
    toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
    toolbar.pack_propagate(False)

    title_lbl = tk.Label(toolbar, text="📊 Check Capture OCR V6.1", font=("Segoe UI", 11, "bold"))
    app.theme_manager.register_widget(title_lbl, {"bg": "primary", "fg": "white"})
    title_lbl.pack(side="left", padx=8, pady=6)

    center_controls_container = tk.Frame(toolbar)
    app.theme_manager.register_widget(center_controls_container, {"bg": "primary"})
    center_controls_container.pack(side="left", expand=True, fill="none")

    controls_frame = tk.Frame(center_controls_container)
    app.theme_manager.register_widget(controls_frame, {"bg": "primary"})
    controls_frame.pack(side="top", anchor="center")

    app.run_btn = tk.Button(
        controls_frame,
        text="🚀 OCR 시작 (F5)",
        command=app.run_ocr_process,
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        cursor="hand2",
    )
    app.theme_manager.register_widget(
        app.run_btn,
        {"bg": "success", "fg": "white", "activebackground": "dark", "activeforeground": "white"},
    )
    app.run_btn.pack(side="left", padx=(0, 5))

    app.stop_btn = tk.Button(
        controls_frame,
        text="⏹️ 중단",
        command=app.stop_processing_ui_initiated,
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        cursor="hand2",
    )
    app.theme_manager.register_widget(
        app.stop_btn,
        {"bg": "danger", "fg": "white", "activebackground": "dark", "activeforeground": "white"},
    )
    app.stop_btn.pack(side="left", padx=(0, 15))

    theme_lbl = tk.Label(toolbar, text="", font=("Segoe UI", 9))
    app.theme_manager.register_widget(theme_lbl, {"bg": "primary", "fg": "white"})
    theme_lbl.pack(side="right", padx=(0, 3))

    app.theme_combo = ttk.Combobox(
        toolbar,
        textvariable=app.theme_var,
        width=12,
        state="readonly",
        font=("Segoe UI", 8),
        style="TCombobox",
    )
    app.theme_combo["values"] = [theme["name"] for theme in app.theme_manager.available_themes.values()]
    app.theme_combo.set(app.theme_manager.available_themes[app.theme_manager.current_theme_key]["name"])
    app.theme_combo.pack(side="right", padx=(0, 8))
    app.theme_combo.bind("<<ComboboxSelected>>", lambda _event: app.theme_manager.change_theme(
        next(
            key
            for key, theme_val in app.theme_manager.available_themes.items()
            if theme_val["name"] == app.theme_var.get()
        )
    ))
