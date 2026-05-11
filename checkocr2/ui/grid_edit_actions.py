"""Grid cell edit actions for the legacy Tk shell."""

from __future__ import annotations

import tkinter as tk
from typing import Any


def on_cell_double_click(app: Any, event: Any) -> None:
    if not app.grid_tree:
        return

    if hasattr(app, "_editing_cell_entry") and app._editing_cell_entry.winfo_exists():
        app._editing_cell_entry.destroy()

    item_id = app.grid_tree.identify_row(event.y)
    column_id = app.grid_tree.identify_column(event.x)

    if not item_id or not column_id:
        return

    col_index = int(column_id.replace("#", "")) - 1
    if col_index < 0:
        return

    col_name = app.grid_tree["columns"][col_index]
    row_index = app.grid_tree.index(item_id)

    if not (0 <= row_index < len(app.data_manager.excel_data)):
        return

    x, y, width, height = app.grid_tree.bbox(item_id, column_id)

    current_value = app.data_manager.excel_data[row_index].get(col_name, "")
    app._editing_cell_entry = tk.Entry(app.grid_tree, font=("Segoe UI", 9))
    app.theme_manager.register_widget(
        app._editing_cell_entry,
        {"bg": "white", "fg": "on_surface", "insertbackground": "on_surface", "relief": "solid", "bd": 1},
    )
    app.theme_manager.apply_theme_to_all_widgets()

    app._editing_cell_entry.place(x=x, y=y, width=width, height=height)
    app._editing_cell_entry.insert(0, current_value)
    app._editing_cell_entry.focus_set()
    app._editing_cell_entry.select_range(0, tk.END)

    app._editing_cell_entry.bind("<Return>", lambda _event, ri=row_index, cn=col_name: app._save_cell_edit(ri, cn))
    app._editing_cell_entry.bind("<KP_Enter>", lambda _event, ri=row_index, cn=col_name: app._save_cell_edit(ri, cn))
    app._editing_cell_entry.bind("<Escape>", lambda _event: app._cancel_cell_edit())
    app._editing_cell_entry.bind(
        "<FocusOut>",
        lambda _event, ri=row_index, cn=col_name: app._save_cell_edit_on_focus_out(ri, cn),
    )

    app._current_edit_info = {"row_index": row_index, "col_name": col_name}


def save_cell_edit_on_focus_out(app: Any, row_index: int, col_name: str) -> None:
    if hasattr(app, "_editing_cell_entry") and app._editing_cell_entry.winfo_exists():
        app._save_cell_edit(row_index, col_name)


def save_cell_edit(app: Any, row_index: int, col_name: str) -> str:
    if hasattr(app, "_editing_cell_entry") and app._editing_cell_entry.winfo_exists():
        new_value = app._editing_cell_entry.get()
        app._editing_cell_entry.destroy()
        del app._editing_cell_entry

        if app.data_manager.update_grid_cell_data(row_index, col_name, new_value):
            app.refresh_grid_ui()
            if hasattr(app, "_current_edit_info"):
                del app._current_edit_info
    return "break"


def cancel_cell_edit(app: Any) -> str:
    if hasattr(app, "_editing_cell_entry") and app._editing_cell_entry.winfo_exists():
        app._editing_cell_entry.destroy()
        del app._editing_cell_entry
    if hasattr(app, "_current_edit_info"):
        del app._current_edit_info
    return "break"
