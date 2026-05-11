"""Legacy Tk queue message dispatch for the CheckOCR2 shell."""

from __future__ import annotations

import logging
import queue
from collections.abc import Callable, Sequence
from typing import Any, Protocol

from checkocr2.events import parse_legacy_finalize_export
from checkocr2.runtime_state import RuntimeState


class QueueDispatcherHost(Protocol):
    message_queue: queue.Queue
    logger: logging.Logger
    ocr_initializing: bool

    def _update_log_text_widget(self, message: str, level_name: str = "INFO") -> None:
        ...

    def _set_runtime_state(self, state: RuntimeState) -> None:
        ...

    def _on_work_complete_ui_only(self, summary_message: str) -> None:
        ...

    def _on_work_stopped(self) -> None:
        ...

    def _handle_grid_update(self, data: object) -> None:
        ...

    def _generate_ocr_summary_internal(self, processed_count: int, total_items: int) -> str:
        ...

    def _finalize_export_and_complete(
        self,
        output_dir: str,
        input_path: str,
        summary: str,
    ) -> None:
        ...


ShowError = Callable[[str, str], None]


def process_legacy_message_queue(
    app: QueueDispatcherHost,
    *,
    show_error: ShowError,
) -> int:
    processed = 0
    try:
        while True:
            msg_type, *data = app.message_queue.get_nowait()
            dispatch_legacy_message(app, msg_type, data, show_error=show_error)
            processed += 1
    except queue.Empty:
        return processed


def dispatch_legacy_message(
    app: QueueDispatcherHost,
    msg_type: str,
    data: Sequence[Any],
    *,
    show_error: ShowError,
) -> None:
    if msg_type == "log":
        dispatch_log_message(app, data)
    elif msg_type == "log_display":
        level_name, formatted_message = data[0], data[1]
        app._update_log_text_widget(formatted_message, level_name)
    elif msg_type == "error_messagebox":
        title, message = data[0], data[1]
        show_error(title, message)
    elif msg_type == "ocr_ready":
        dispatch_ocr_ready_message(app, data)
    elif msg_type == "complete":
        summary_message = data[0] if data else ""
        app._on_work_complete_ui_only(summary_message)
    elif msg_type == "stopped":
        app._on_work_stopped()
    elif msg_type == "grid_update":
        app._handle_grid_update(data[0])
    elif msg_type == "finalize_export_and_complete":
        dispatch_finalize_export_message(app, data)


def dispatch_log_message(app: QueueDispatcherHost, data: Sequence[Any]) -> None:
    if len(data) >= 2:
        message, level_str = data[0], data[1]
        level = getattr(logging, str(level_str).upper(), logging.INFO)
        app.logger.log(level, message)
    else:
        message = data[0] if data else "알 수 없는 로그 메시지"
        app.logger.info(message)


def dispatch_ocr_ready_message(app: QueueDispatcherHost, data: Sequence[Any]) -> None:
    ready = bool(data[0]) if data else False
    app.ocr_initializing = False
    if ready:
        app._set_runtime_state(RuntimeState.READY)
        app.message_queue.put(("log", "OCR 엔진 준비 완료", "INFO"))
    else:
        app._set_runtime_state(RuntimeState.ERROR)


def dispatch_finalize_export_message(app: QueueDispatcherHost, data: Sequence[Any]) -> None:
    try:
        request = parse_legacy_finalize_export(data)
    except (TypeError, ValueError):
        app.logger.error("잘못된 finalize_export_and_complete 메시지 형식: %s", data)
        return

    summary = app._generate_ocr_summary_internal(request.processed_count, request.total_items)
    app._finalize_export_and_complete(request.output_dir, request.input_path, summary)


def queue_check_interval(is_running: bool) -> int:
    return 50 if is_running else 100
