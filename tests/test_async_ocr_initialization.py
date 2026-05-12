from __future__ import annotations

import logging
import queue
from types import SimpleNamespace

from checkocr2.runtime_state import RuntimeState, runtime_state_ui


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


def make_workflow_manager_for_initialize(ocr_module):
    events = queue.Queue()
    manager = ocr_module.OCRWorkflowManager(
        app_ref=None,
        logger=logging.getLogger("tests.async_ocr.manager"),
        message_queue=events,
        work_controller=ocr_module.WorkController(),
        settings_manager=SimpleNamespace(),
        data_manager=SimpleNamespace(),
    )
    return manager, events


def test_async_ocr_initialization_enables_start_after_ready(ocr_module, monkeypatch):
    monkeypatch.setattr(ocr_module.threading, "Thread", ImmediateThread)
    app = make_app(ocr_module, ready=True)

    app.start_ocr_initialization_async()
    app.check_queue()

    assert app.ocr_initializing is False
    assert app.runtime_state is RuntimeState.READY
    assert app.run_btn.last_config == {"state": "normal", "text": "🚀 OCR 시작 (F5)"}
    assert app.stop_btn.last_config == {"state": "disabled"}


def test_async_ocr_initialization_keeps_start_disabled_after_failure(
    ocr_module, monkeypatch
):
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


def test_runtime_state_update_without_smoke_env_does_not_require_workflow_manager(
    ocr_module, monkeypatch
):
    monkeypatch.delenv("CHECKOCR2_PACKAGE_SMOKE_STATUS_FILE", raising=False)
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    app.runtime_state = RuntimeState.STARTING
    app.run_btn = FakeButton()
    app.stop_btn = FakeButton()

    app._set_runtime_state(RuntimeState.READY)

    ready_ui = runtime_state_ui(RuntimeState.READY)
    assert app.runtime_state is RuntimeState.READY
    assert app.run_btn.last_config == {
        "state": ready_ui.run_button_state,
        "text": ready_ui.run_button_text,
    }
    assert app.stop_btn.last_config == {"state": ready_ui.stop_button_state}


def test_run_ocr_process_is_blocked_while_ocr_is_loading(
    ocr_module, monkeypatch, tmp_path
):
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


def test_legacy_app_ocr_initialization_method_delegates(ocr_module, monkeypatch):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "start_ocr_initialization_action",
        lambda actual_app, **kwargs: calls.append((actual_app, kwargs)),
    )

    app.start_ocr_initialization_async()

    assert calls
    assert calls[0][0] is app
    assert calls[0][1]["thread_factory"] is ocr_module.threading.Thread


def test_legacy_workflow_manager_initialize_ocr_delegates(
    ocr_module, ocr_workflow_module, monkeypatch
):
    manager, _events = make_workflow_manager_for_initialize(ocr_module)
    reader = object()
    calls = []

    monkeypatch.setattr(
        ocr_workflow_module,
        "initialize_easyocr_reader_with_fallback",
        lambda **kwargs: calls.append(kwargs) or reader,
    )

    manager.initialize_ocr()

    assert manager.ocr_reader is reader
    assert calls
    assert calls[0]["logger"] is manager.logger
    assert calls[0]["settings_manager"] is manager.settings_manager
    assert calls[0]["message_queue"] is manager.message_queue
