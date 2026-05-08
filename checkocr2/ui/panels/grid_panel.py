"""Excel grid panel construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Protocol


class ThemeManagerLike(Protocol):
    def register_widget(self, widget: object, style_config: dict[str, object]) -> None:
        ...


class GridPanelHost(Protocol):
    theme_manager: ThemeManagerLike
    grid_tree: object
    grid_status_label: object
    grid_progress_label: object

    def _create_section_frame_styled(
        self,
        parent: object,
        title: str,
        fill_parent: bool = False,
    ) -> object:
        ...

    def load_excel_to_grid(self) -> None:
        ...

    def add_empty_row_ui(self) -> None:
        ...

    def paste_from_clipboard_ui(self) -> None:
        ...

    def delete_selected_rows_ui(self) -> None:
        ...

    def clear_all_data_ui(self) -> None:
        ...

    def copy_selected_rows_ui(self) -> None:
        ...

    def on_cell_double_click_ui(self, event: object) -> None:
        ...

    def show_context_menu_ui(self, event: object) -> None:
        ...

    def refresh_grid_tags(self) -> None:
        ...


def create_grid_panel(app: GridPanelHost, parent: object) -> None:
    grid_section = app._create_section_frame_styled(parent, "📊 Excel 데이터 그리드", fill_parent=True)

    control_frame = tk.Frame(grid_section)
    app.theme_manager.register_widget(control_frame, {"bg": "white"})
    control_frame.pack(fill="x", pady=(0, 10))

    left_controls = tk.Frame(control_frame)
    app.theme_manager.register_widget(left_controls, {"bg": "white"})
    left_controls.pack(side="left", fill="x", expand=True, padx=(0, 5))

    left_buttons = [
        ("📁 Excel 로드", app.load_excel_to_grid, {"bg": "primary", "fg": "white", "activebackground": "dark"}),
        ("➕ 행 추가", app.add_empty_row_ui, {"bg": "success", "fg": "white", "activebackground": "dark"}),
        ("📋 붙여넣기", app.paste_from_clipboard_ui, {"bg": "secondary", "fg": "white", "activebackground": "dark"}),
    ]
    for text, command, style in left_buttons:
        button = tk.Button(
            left_controls,
            text=text,
            command=command,
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
        )
        app.theme_manager.register_widget(button, style)
        button.pack(side="left", padx=(0, 5))

    right_controls = tk.Frame(control_frame)
    app.theme_manager.register_widget(right_controls, {"bg": "white"})
    right_controls.pack(side="right")

    right_buttons = [
        ("🗑️ 선택 삭제", app.delete_selected_rows_ui, {"bg": "danger", "fg": "white", "activebackground": "dark"}),
        ("🧹 전체 삭제", app.clear_all_data_ui, {"bg": "warning", "fg": "on_surface", "activebackground": "dark"}),
    ]
    for text, command, style in right_buttons:
        button = tk.Button(
            right_controls,
            text=text,
            command=command,
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
        )
        app.theme_manager.register_widget(button, style)
        button.pack(side="right", padx=(5, 0))

    tree_frame = tk.Frame(grid_section)
    app.theme_manager.register_widget(tree_frame, {"bg": "white"})
    tree_frame.pack(fill="both", expand=True)

    columns = ("종목코드", "종목명", "날짜", "금리", "상태")
    app.grid_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", style="Treeview")

    for col_name in columns:
        app.grid_tree.heading(col_name, text=col_name)
    col_widths = {"종목코드": 95, "종목명": 180, "날짜": 120, "금리": 95, "상태": 100}
    for col_name, width in col_widths.items():
        app.grid_tree.column(
            col_name,
            width=width,
            anchor="center",
            minwidth=width - 20,
            stretch=tk.YES,
        )

    v_scrollbar = ttk.Scrollbar(
        tree_frame,
        orient="vertical",
        command=app.grid_tree.yview,
        style="TScrollbar",
    )
    h_scrollbar = ttk.Scrollbar(
        tree_frame,
        orient="horizontal",
        command=app.grid_tree.xview,
        style="TScrollbar",
    )
    app.grid_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

    app.grid_tree.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")

    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    app.grid_tree.bind("<Double-1>", app.on_cell_double_click_ui)
    app.grid_tree.bind("<Button-3>", app.show_context_menu_ui)
    app.grid_tree.bind("<Delete>", lambda _event: app.delete_selected_rows_ui())
    app.grid_tree.bind("<Control-c>", lambda _event: app.copy_selected_rows_ui())
    app.grid_tree.bind("<Control-v>", lambda _event: app.paste_from_clipboard_ui())

    status_frame = tk.Frame(grid_section)
    app.theme_manager.register_widget(status_frame, {"bg": "white"})
    status_frame.pack(fill="x", pady=(10, 0))

    app.grid_status_label = tk.Label(
        status_frame,
        text="총 0행 | 완료: 0 | 대기: 0 | 오류: 0",
        font=("Segoe UI", 9),
    )
    app.theme_manager.register_widget(app.grid_status_label, {"bg": "white", "fg": "on_surface"})
    app.grid_status_label.pack(side="left")

    app.grid_progress_label = tk.Label(
        status_frame,
        text="진행률: 0.0%",
        font=("Segoe UI", 9, "bold"),
    )
    app.theme_manager.register_widget(app.grid_progress_label, {"bg": "white", "fg": "primary"})
    app.grid_progress_label.pack(side="right")

    app.refresh_grid_tags()
