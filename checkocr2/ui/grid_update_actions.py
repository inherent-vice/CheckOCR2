"""Grid update dispatch actions for the legacy Tk shell."""

from __future__ import annotations

import tkinter as tk
from typing import Any

from checkocr2.events import parse_legacy_grid_update
from checkocr2.table_model import apply_grid_update


def handle_grid_update(app: Any, data: object) -> None:
    try:
        result = apply_grid_update(app.data_manager.excel_data, parse_legacy_grid_update(data))
        if result.should_scroll and app.grid_tree and result.row_index is not None:
            children = app.grid_tree.get_children()
            if result.row_index < len(children):
                app.grid_tree.see(children[result.row_index])
        if result.should_refresh:
            if result.row_index is not None:
                app.logger.debug(
                    f"[_handle_grid_update] {result.row_index}번 항목 업데이트 후: "
                    f"{app.data_manager.excel_data[result.row_index]}"
                )
            app.refresh_grid_ui()
    except (KeyError, tk.TclError, TypeError, ValueError) as exc:
        app.logger.error(f"그리드 업데이트 중 오류: {exc}, 데이터: {data}")
