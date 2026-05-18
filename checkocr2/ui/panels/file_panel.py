"""File and output-folder panel construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from typing import Protocol

from checkocr2.ui.tooltip import ToolTip


class ThemeManagerLike(Protocol):
    def register_widget(self, widget: object, style_config: dict[str, object]) -> None:
        ...


class FilePanelHost(Protocol):
    theme_manager: ThemeManagerLike
    input_excel_path: object
    output_folder_path: object
    excel_entry: object
    output_entry: object
    open_folder_btn: object

    def _create_section_frame_styled(
        self,
        parent: object,
        title: str,
        fill_parent: bool = False,
    ) -> object:
        ...

    def browse_input_excel(self) -> None:
        ...

    def browse_output_folder(self) -> None:
        ...

    def open_output_folder(self) -> None:
        ...


def create_file_panel(app: FilePanelHost, parent: object) -> None:
    section = app._create_section_frame_styled(parent, "📁 파일 설정")
    common_font = ("Segoe UI", 9)
    btn_font = ("Segoe UI", 9)
    btn_width = 5
    btn_height = 1

    excel_frame = tk.Frame(section)
    app.theme_manager.register_widget(excel_frame, {"bg": "white"})
    excel_frame.pack(fill="x", pady=(0, 5))

    excel_lbl = tk.Label(excel_frame, text="Excel 입력 파일:", font=(common_font[0], common_font[1], "bold"))
    app.theme_manager.register_widget(excel_lbl, {"bg": "white", "fg": "on_surface"})
    excel_lbl.pack(anchor="w", pady=(0, 2))

    excel_input_frame = tk.Frame(excel_frame)
    app.theme_manager.register_widget(excel_input_frame, {"bg": "white"})
    excel_input_frame.pack(fill="x")

    app.excel_entry = tk.Entry(
        excel_input_frame,
        textvariable=app.input_excel_path,
        font=common_font,
        relief="solid",
        bd=1,
    )
    app.theme_manager.register_widget(app.excel_entry, {"bg": "white", "fg": "on_surface"})
    app.excel_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

    excel_browse_btn = tk.Button(
        excel_input_frame,
        text="찾기",
        command=app.browse_input_excel,
        font=btn_font,
        relief="flat",
        cursor="hand2",
        width=btn_width,
        height=btn_height,
        pady=0,
    )
    app.theme_manager.register_widget(
        excel_browse_btn,
        {"bg": "secondary", "fg": "white", "activebackground": "dark"},
    )
    excel_browse_btn.pack(side="right")

    output_frame = tk.Frame(section)
    app.theme_manager.register_widget(output_frame, {"bg": "white"})
    output_frame.pack(fill="x", pady=(8, 0))

    output_lbl = tk.Label(output_frame, text="출력 폴더:", font=(common_font[0], common_font[1], "bold"))
    app.theme_manager.register_widget(output_lbl, {"bg": "white", "fg": "on_surface"})
    output_lbl.pack(anchor="w", pady=(0, 2))

    output_input_frame = tk.Frame(output_frame)
    app.theme_manager.register_widget(output_input_frame, {"bg": "white"})
    output_input_frame.pack(fill="x")

    app.output_entry = tk.Entry(
        output_input_frame,
        textvariable=app.output_folder_path,
        font=common_font,
        relief="solid",
        bd=1,
    )
    app.theme_manager.register_widget(
        app.output_entry,
        {"bg": "white", "fg": "on_surface", "relief": "solid", "bd": 1},
    )
    app.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

    output_browse_btn = tk.Button(
        output_input_frame,
        text="찾기",
        command=app.browse_output_folder,
        font=btn_font,
        relief="flat",
        cursor="hand2",
        width=btn_width,
        height=btn_height,
        pady=0,
    )
    app.theme_manager.register_widget(
        output_browse_btn,
        {"bg": "secondary", "fg": "white", "activebackground": "dark"},
    )
    output_browse_btn.pack(side="right")

    app.open_folder_btn = tk.Button(
        output_input_frame,
        text="📂",
        command=app.open_output_folder,
        font=btn_font,
        relief="flat",
        cursor="hand2",
        width=3,
        height=btn_height,
        pady=0,
    )
    app.theme_manager.register_widget(
        app.open_folder_btn,
        {"bg": "primary", "fg": "white", "activebackground": "dark"},
    )
    app.open_folder_btn.pack(side="left", padx=(5, 0))
    ToolTip(app.open_folder_btn, "출력 폴더 열기")
