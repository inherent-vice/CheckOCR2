"""Keyboard shortcut actions for the legacy Tk shell."""

from __future__ import annotations

from typing import Any


def setup_keyboard_shortcuts(app: Any) -> None:
    app.focus_set()
    app.bind_all("<Control-s>", lambda _event: app.quick_save_settings())
    app.bind_all("<Control-l>", lambda _event: app.load_last_settings())
    app.bind_all("<Control-o>", lambda _event: app.load_excel_to_grid())
    app.bind_all("<F5>", lambda _event: app.handle_f5_key())
    app.bind_all("<Escape>", lambda _event: app.stop_processing_ui_initiated())
    app.bind_all("<F1>", lambda _event: app.show_shortcuts())


def handle_f5_key(app: Any) -> None:
    if app.work_controller.is_running:
        app.stop_processing_ui_initiated()
    else:
        app.run_ocr_process()
