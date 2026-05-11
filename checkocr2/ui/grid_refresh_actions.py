"""Grid refresh and status-label actions for the legacy Tk shell."""

from __future__ import annotations

from typing import Any

from checkocr2.table_model import (
    format_grid_progress_text,
    format_grid_status_text,
    grid_row_tags,
    grid_row_values,
    summarize_grid_rows,
)


def refresh_grid(app: Any) -> None:
    if not app.grid_tree:
        return
    for item in app.grid_tree.get_children():
        app.grid_tree.delete(item)

    for index, row in enumerate(app.data_manager.excel_data):
        tags = grid_row_tags(
            row,
            row_index=index,
            current_processing_index=app.data_manager.current_processing_index,
            is_running=app.work_controller.is_running,
        )
        app.grid_tree.insert("", "end", values=grid_row_values(row), tags=tags)
    app.update_grid_status_labels()


def update_grid_status_labels(app: Any) -> None:
    if not hasattr(app, "grid_status_label"):
        return
    summary = summarize_grid_rows(app.data_manager.excel_data)
    app.grid_status_label.config(text=format_grid_status_text(summary))
    if hasattr(app, "grid_progress_label"):
        app.grid_progress_label.config(text=format_grid_progress_text(summary))
