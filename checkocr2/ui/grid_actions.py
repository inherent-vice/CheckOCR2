"""Grid action helpers for the legacy Tk shell."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any

from checkocr2.table_model import rates_for_copy, rows_for_copy


def scroll_to_last_grid_row(app: Any) -> None:
    if not app.grid_tree:
        return
    children = app.grid_tree.get_children()
    if children:
        app.grid_tree.see(children[-1])


def selected_grid_indices(app: Any) -> list[int]:
    if not app.grid_tree:
        return []
    return [app.grid_tree.index(item) for item in app.grid_tree.selection()]


def add_empty_row(app: Any) -> None:
    app.data_manager.add_empty_row_data()
    app.refresh_grid_ui()
    scroll_to_last_grid_row(app)


def paste_from_clipboard(app: Any) -> None:
    try:
        clipboard_content = app.clipboard_get()
        added_count = app.data_manager.paste_from_clipboard_data(clipboard_content)
        if added_count > 0:
            app.refresh_grid_ui()
            messagebox.showinfo("성공", f"{added_count}행을 추가했습니다.", parent=app)
            scroll_to_last_grid_row(app)
        else:
            messagebox.showwarning(
                "경고",
                "붙여넣을 유효한 데이터가 없습니다 (탭으로 구분된 데이터 필요).",
                parent=app,
            )
    except tk.TclError:
        messagebox.showerror("오류", "클립보드에 텍스트 데이터가 없습니다.", parent=app)


def delete_selected_rows(app: Any) -> None:
    if not app.grid_tree:
        return
    selected_items = app.grid_tree.selection()
    if not selected_items:
        messagebox.showwarning("경고", "삭제할 행을 선택해주세요.", parent=app)
        return
    indices_to_delete = [app.grid_tree.index(item) for item in selected_items]
    if not messagebox.askyesno("확인", f"{len(selected_items)}개의 행을 삭제하시겠습니까?", parent=app):
        return

    app.data_manager.delete_rows_data(indices_to_delete)
    app.refresh_grid_ui()


def clear_all_data(app: Any) -> None:
    if app.data_manager.excel_data and not messagebox.askyesno(
        "확인",
        "모든 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
        parent=app,
    ):
        return
    app.data_manager.clear_all_data_internal()
    app.refresh_grid_ui()


def copy_selected_rows(app: Any) -> None:
    if not app.grid_tree:
        return
    selected_items = app.grid_tree.selection()
    if not selected_items:
        return

    selection = rows_for_copy(app.data_manager.excel_data, selected_grid_indices(app))
    if selection.has_items:
        app.clipboard_clear()
        app.clipboard_append(selection.text)
        app.logger.info(f"{selection.count}개 행이 클립보드에 복사되었습니다.")


def copy_selected_rates(app: Any) -> None:
    if not app.grid_tree:
        return
    selected_items = app.grid_tree.selection()
    if not selected_items:
        messagebox.showwarning("경고", "복사할 행을 선택해주세요.", parent=app)
        return

    selection = rates_for_copy(app.data_manager.excel_data, selected_grid_indices(app))
    if selection.has_items:
        app.clipboard_clear()
        app.clipboard_append(selection.text)
        app.logger.info(f"선택된 {selection.count}개 행의 금리가 클립보드에 복사되었습니다.")
    else:
        app.logger.info("선택된 행에 금리 데이터가 없습니다.")
