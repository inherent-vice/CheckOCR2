"""OCR run/stop controller actions for the legacy Tk shell."""

from __future__ import annotations

import os
from collections.abc import Callable
from tkinter import messagebox
from typing import Any

from checkocr2.runtime_state import RuntimeState
from checkocr2.ui.start_validation import ERROR, validate_ocr_start
from checkocr2.worker import start_daemon_worker


def stop_processing(app: Any) -> None:
    if app.work_controller.is_running:
        message = app.work_controller.stop_work()
        app._set_runtime_state(RuntimeState.STOPPING)
        app.message_queue.put(("log", message, "INFO"))


def run_ocr_process(
    app: Any,
    *,
    start_worker: Callable[..., Any] = start_daemon_worker,
) -> None:
    if app.work_controller.is_running:
        app.stop_processing_ui_initiated()
        return
    if not app._validate_inputs_for_ocr():
        return

    app.work_controller.start_work()
    app._set_runtime_state(RuntimeState.RUNNING)
    current_ui_settings = app.get_current_ui_settings()
    output_dir = app.output_folder_path.get().strip()
    save_details = app.save_detail_images.get()

    app.worker_thread = start_worker(
        app.ocr_workflow_manager.execute_ocr_workflow_threaded,
        current_ui_settings,
        output_dir,
        save_details,
        name="checkocr2-ocr-workflow",
    )


def validate_inputs_for_ocr(
    app: Any,
    *,
    isdir: Callable[[str], bool] = os.path.isdir,
    showerror: Callable[..., object] | None = None,
    showwarning: Callable[..., object] | None = None,
    validator: Callable[..., Any] = validate_ocr_start,
) -> bool:
    error_dialog = showerror if showerror is not None else messagebox.showerror
    warning_dialog = (
        showwarning
        if showwarning is not None
        else getattr(messagebox, "showwarning", messagebox.showinfo)
    )

    output_dir = app.output_folder_path.get().strip()
    validation = validator(
        rows=app.data_manager.excel_data,
        output_dir_exists=lambda: bool(output_dir and isdir(output_dir)),
        ocr_initializing=app.ocr_initializing,
        ocr_ready=bool(app.ocr_workflow_manager.ocr_reader),
    )
    if not validation.is_valid:
        show_message = error_dialog if validation.severity == ERROR else warning_dialog
        show_message(validation.title, validation.message, parent=app)
        return False
    return True
