"""OCR run/stop controller actions for the legacy Tk shell."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from checkocr2.runtime_state import RuntimeState
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
