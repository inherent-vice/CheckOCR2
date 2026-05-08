from __future__ import annotations

import logging
import queue


class FakeButton:
    def __init__(self):
        self.config_calls = []

    def config(self, **kwargs):
        self.config_calls.append(kwargs)


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
    assert app.run_btn.config_calls[-1] == {"state": "normal", "text": "🚀 OCR 시작 (F5)"}


def test_async_ocr_initialization_keeps_start_disabled_after_failure(ocr_module, monkeypatch):
    monkeypatch.setattr(ocr_module.threading, "Thread", ImmediateThread)
    app = make_app(ocr_module, ready=False)

    app.start_ocr_initialization_async()
    app.check_queue()

    assert app.ocr_initializing is False
    assert app.run_btn.config_calls[-1] == {"state": "disabled", "text": "OCR 초기화 실패"}
