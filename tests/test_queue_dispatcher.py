from __future__ import annotations

import queue

from checkocr2.runtime_state import RuntimeState
from checkocr2.ui.queue_dispatcher import process_legacy_message_queue, queue_check_interval


class FakeLogger:
    def __init__(self):
        self.logs = []
        self.infos = []
        self.errors = []

    def log(self, level, message):
        self.logs.append((level, message))

    def info(self, message):
        self.infos.append(message)

    def error(self, message, *args):
        self.errors.append(message % args if args else message)


class FakeApp:
    def __init__(self):
        self.message_queue = queue.Queue()
        self.logger = FakeLogger()
        self.ocr_initializing = True
        self.runtime_states = []
        self.log_display_updates = []
        self.completed = []
        self.stopped = 0
        self.grid_updates = []
        self.finalized = []

    def _update_log_text_widget(self, message, level_name="INFO"):
        self.log_display_updates.append((message, level_name))

    def _set_runtime_state(self, state):
        self.runtime_states.append(state)

    def _on_work_complete_ui_only(self, summary_message):
        self.completed.append(summary_message)

    def _on_work_stopped(self):
        self.stopped += 1

    def _handle_grid_update(self, data):
        self.grid_updates.append(data)

    def _generate_ocr_summary_internal(self, processed_count, total_items):
        return f"{processed_count}/{total_items}"

    def _finalize_export_and_complete(self, output_dir, input_path, summary):
        self.finalized.append((output_dir, input_path, summary))


def test_process_legacy_message_queue_dispatches_ui_events_in_order():
    app = FakeApp()
    shown_errors = []
    for event in [
        ("log", "started", "WARNING"),
        ("log_display", "INFO", "formatted"),
        ("error_messagebox", "Title", "Message"),
        ("ocr_ready", True),
        ("complete", "summary"),
        ("stopped",),
        ("grid_update", {"row": 1}),
        ("finalize_export_and_complete", "out", "input.xlsx", 2, 3),
    ]:
        app.message_queue.put(event)

    processed = process_legacy_message_queue(app, show_error=lambda title, msg: shown_errors.append((title, msg)))

    assert processed == 9
    assert app.logger.logs == [(30, "started"), (20, "OCR 엔진 준비 완료")]
    assert app.log_display_updates == [("formatted", "INFO")]
    assert shown_errors == [("Title", "Message")]
    assert app.ocr_initializing is False
    assert app.runtime_states == [RuntimeState.READY]
    assert app.completed == ["summary"]
    assert app.stopped == 1
    assert app.grid_updates == [{"row": 1}]
    assert app.finalized == [("out", "input.xlsx", "2/3")]
    assert app.message_queue.empty()


def test_process_legacy_message_queue_reports_bad_finalize_payload():
    app = FakeApp()
    app.message_queue.put(("finalize_export_and_complete", "bad"))

    processed = process_legacy_message_queue(app, show_error=lambda _title, _msg: None)

    assert processed == 1
    assert app.finalized == []
    assert app.logger.errors == ["잘못된 finalize_export_and_complete 메시지 형식: ['bad']"]


def test_process_legacy_message_queue_preserves_empty_log_fallback():
    app = FakeApp()
    app.message_queue.put(("log",))

    process_legacy_message_queue(app, show_error=lambda _title, _msg: None)

    assert app.logger.infos == ["알 수 없는 로그 메시지"]


def test_queue_check_interval_matches_running_state():
    assert queue_check_interval(True) == 50
    assert queue_check_interval(False) == 100
