"""Menu construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from typing import Protocol


class MenuHost(Protocol):
    def config(self, **kwargs: object) -> None:
        ...

    def load_excel_to_grid(self) -> None:
        ...

    def browse_input_excel(self) -> None:
        ...

    def browse_output_folder(self) -> None:
        ...

    def open_output_folder(self) -> None:
        ...

    def quit_app(self) -> None:
        ...

    def quick_save_settings(self) -> None:
        ...

    def load_last_settings(self) -> None:
        ...

    def show_area_preview(self) -> None:
        ...

    def handle_f5_key(self) -> None:
        ...

    def stop_processing_ui_initiated(self) -> None:
        ...

    def show_shortcuts(self) -> None:
        ...

    def show_about(self) -> None:
        ...


def create_menu(app: MenuHost) -> None:
    menubar = tk.Menu(app)
    app.config(menu=menubar)

    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="파일", menu=file_menu)
    file_menu.add_command(label="Excel 파일 로드 (Ctrl+O)", command=app.load_excel_to_grid, accelerator="Ctrl+O")
    file_menu.add_command(label="Excel 파일 선택", command=app.browse_input_excel)
    file_menu.add_command(label="출력 폴더 선택", command=app.browse_output_folder)
    file_menu.add_command(label="출력 폴더 열기", command=app.open_output_folder)
    file_menu.add_separator()
    file_menu.add_command(label="종료 (Alt+F4)", command=app.quit_app, accelerator="Alt+F4")

    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="설정", menu=settings_menu)
    settings_menu.add_command(
        label="현재 설정 저장 (Ctrl+S)",
        command=app.quick_save_settings,
        accelerator="Ctrl+S",
    )
    settings_menu.add_command(
        label="마지막 설정 불러오기 (Ctrl+L)",
        command=app.load_last_settings,
        accelerator="Ctrl+L",
    )
    settings_menu.add_separator()

    preview_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="미리보기", menu=preview_menu)
    preview_menu.add_command(label="전체 영역 미리보기", command=app.show_area_preview)

    run_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="실행", menu=run_menu)
    run_menu.add_command(label="OCR 시작/중단 (F5)", command=app.handle_f5_key, accelerator="F5")
    run_menu.add_command(
        label="처리 중단 (Esc)",
        command=app.stop_processing_ui_initiated,
        accelerator="Esc",
    )

    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="도움말", menu=help_menu)
    help_menu.add_command(label="키보드 단축키 (F1)", command=app.show_shortcuts, accelerator="F1")
    help_menu.add_command(label="프로그램 정보", command=app.show_about)
