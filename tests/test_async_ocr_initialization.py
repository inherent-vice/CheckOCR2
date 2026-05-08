from __future__ import annotations

import logging
import queue
from types import SimpleNamespace

from checkocr2.runtime_state import RuntimeState


class FakeButton:
    def __init__(self):
        self.config_calls = []

    def config(self, **kwargs):
        self.config_calls.append(kwargs)

    @property
    def last_config(self):
        return self.config_calls[-1]


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


class FakeWorkflow:
    def __init__(self, ready):
        self.ready = ready
        self.ocr_reader = None

    def initialize_ocr(self):
        if self.ready:
            self.ocr_reader = object()


def make_app(ocr_module, ready):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    app.ocr_initializing = False
    app.ocr_workflow_manager = FakeWorkflow(ready)
    app.message_queue = queue.Queue()
    app.run_btn = FakeButton()
    app.stop_btn = FakeButton()
    app.runtime_state = RuntimeState.STARTING
    app.logger = logging.getLogger("tests.async_ocr")
    app.work_controller = ocr_module.WorkController()
    app.after = lambda interval, callback: None
    return app


def test_async_ocr_initialization_enables_start_after_ready(ocr_module, monkeypatch):
    monkeypatch.setattr(ocr_module.threading, "Thread", ImmediateThread)
    app = make_app(ocr_module, ready=True)

    app.start_ocr_initialization_async()
    app.check_queue()

    assert app.ocr_initializing is False
    assert app.runtime_state is RuntimeState.READY
    assert app.run_btn.last_config == {"state": "normal", "text": "🚀 OCR 시작 (F5)"}
    assert app.stop_btn.last_config == {"state": "disabled"}


def test_async_ocr_initialization_keeps_start_disabled_after_failure(ocr_module, monkeypatch):
    monkeypatch.setattr(ocr_module.threading, "Thread", ImmediateThread)
    app = make_app(ocr_module, ready=False)

    app.start_ocr_initialization_async()
    app.check_queue()

    assert app.ocr_initializing is False
    assert app.runtime_state is RuntimeState.ERROR
    assert app.run_btn.last_config == {"state": "disabled", "text": "OCR 초기화 실패"}
    assert app.stop_btn.last_config == {"state": "disabled"}


def test_runtime_state_updates_run_and_stop_buttons(ocr_module):
    app = make_app(ocr_module, ready=True)

    app._set_runtime_state(RuntimeState.RUNNING)

    assert app.runtime_state is RuntimeState.RUNNING
    assert app.run_btn.last_config == {"state": "normal", "text": "⏹️ 중단 (F5)"}
    assert app.stop_btn.last_config == {"state": "normal"}

    app._set_runtime_state(RuntimeState.STOPPING)

    assert app.runtime_state is RuntimeState.STOPPING
    assert app.run_btn.last_config == {"state": "disabled", "text": "중단 중..."}
    assert app.stop_btn.last_config == {"state": "disabled"}


def test_run_ocr_process_is_blocked_while_ocr_is_loading(ocr_module, monkeypatch, tmp_path):
    warnings = []
    app = make_app(ocr_module, ready=False)
    app.ocr_initializing = True
    app.data_manager = SimpleNamespace(excel_data=[{"종목코드": "A001"}])
    app.output_folder_path = SimpleNamespace(get=lambda: str(tmp_path))
    monkeypatch.setattr(
        ocr_module.messagebox,
        "showwarning",
        lambda title, message, parent=None: warnings.append((title, message, parent)),
        raising=False,
    )

    app.run_ocr_process()

    assert app.work_controller.is_running is False
    assert warnings
    assert "OCR" in warnings[0][0]
