"""Preset management panel construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Protocol


class ThemeManagerLike(Protocol):
    def register_widget(self, widget: object, style_config: dict[str, object]) -> None:
        ...


class PresetPanelHost(Protocol):
    theme_manager: ThemeManagerLike
    preset_combo: object
    preset_name_entry: object

    def _create_section_frame_styled(
        self,
        parent: object,
        title: str,
        fill_parent: bool = False,
    ) -> object:
        ...

    def apply_selected_preset(self) -> None:
        ...

    def delete_selected_preset(self) -> None:
        ...

    def save_current_as_preset(self) -> None:
        ...

    def update_preset_combo(self) -> None:
        ...


def create_preset_panel(app: PresetPanelHost, parent: object) -> None:
    section = app._create_section_frame_styled(parent, "💾 프리셋 관리", fill_parent=True)
    common_font = ("Segoe UI", 9)
    btn_font = ("Segoe UI", 9)
    btn_width = 6
    btn_height = 1

    preset_load_frame = tk.Frame(section)
    app.theme_manager.register_widget(preset_load_frame, {"bg": "white"})
    preset_load_frame.pack(fill="x", pady=(0, 8))

    preset_lbl = tk.Label(
        preset_load_frame,
        text="저장된 프리셋:",
        font=(common_font[0], common_font[1], "bold"),
    )
    app.theme_manager.register_widget(preset_lbl, {"bg": "white", "fg": "on_surface"})
    preset_lbl.pack(anchor="w", pady=(0, 2))

    preset_control_frame = tk.Frame(preset_load_frame)
    app.theme_manager.register_widget(preset_control_frame, {"bg": "white"})
    preset_control_frame.pack(fill="x")

    app.preset_combo = ttk.Combobox(
        preset_control_frame,
        state="readonly",
        font=common_font,
        style="TCombobox",
    )
    app.preset_combo.pack(side="left", fill="x", expand=True, padx=(0, 5))

    apply_preset_btn = tk.Button(
        preset_control_frame,
        text="적용",
        command=app.apply_selected_preset,
        font=btn_font,
        relief="flat",
        cursor="hand2",
        width=btn_width,
        height=btn_height,
        pady=0,
    )
    app.theme_manager.register_widget(
        apply_preset_btn,
        {"bg": "success", "fg": "white", "activebackground": "dark"},
    )
    apply_preset_btn.pack(side="right", padx=(0, 5))

    delete_preset_btn = tk.Button(
        preset_control_frame,
        text="삭제",
        command=app.delete_selected_preset,
        font=btn_font,
        relief="flat",
        cursor="hand2",
        width=btn_width,
        height=btn_height,
        pady=0,
    )
    app.theme_manager.register_widget(
        delete_preset_btn,
        {"bg": "danger", "fg": "white", "activebackground": "dark"},
    )
    delete_preset_btn.pack(side="right")

    preset_save_frame = tk.Frame(section)
    app.theme_manager.register_widget(preset_save_frame, {"bg": "white"})
    preset_save_frame.pack(fill="x", pady=(15, 0))

    save_preset_lbl = tk.Label(
        preset_save_frame,
        text="새 프리셋 저장:",
        font=(common_font[0], common_font[1], "bold"),
    )
    app.theme_manager.register_widget(save_preset_lbl, {"bg": "white", "fg": "on_surface"})
    save_preset_lbl.pack(anchor="w", pady=(0, 2))

    save_control_frame = tk.Frame(preset_save_frame)
    app.theme_manager.register_widget(save_control_frame, {"bg": "white"})
    save_control_frame.pack(fill="x")

    app.preset_name_entry = tk.Entry(
        save_control_frame,
        font=common_font,
        relief="solid",
        bd=1,
    )
    app.theme_manager.register_widget(app.preset_name_entry, {"bg": "white", "fg": "on_surface"})
    app.preset_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
    app.preset_name_entry.insert(0, "새 프리셋 이름")

    save_preset_btn = tk.Button(
        save_control_frame,
        text="저장",
        command=app.save_current_as_preset,
        font=btn_font,
        relief="flat",
        cursor="hand2",
        width=btn_width,
        height=btn_height,
        pady=0,
    )
    app.theme_manager.register_widget(
        save_preset_btn,
        {"bg": "accent", "fg": "white", "activebackground": "dark"},
    )
    save_preset_btn.pack(side="right")

    app.update_preset_combo()
