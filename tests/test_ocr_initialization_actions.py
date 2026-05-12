from __future__ import annotations

import queue

from checkocr2.runtime_state import RuntimeState
from checkocr2.ui.ocr_initialization_actions import start_ocr_initialization


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


class FakeWorkflow:
    def __init__(self, ready=False):
        self.ready = ready
        self.ocr_reader = None
        self.initialize_calls = 0

    def initialize_ocr(self):
        self.initialize_calls += 1
        if self.ready:
            self.ocr_reader = object()


class FakeApp:
    def __init__(self, *, ready=False):
        self.ocr_initializing = False
        self.ocr_workflow_manager = FakeWorkflow(ready=ready)
        self.message_queue = queue.Queue()
        self.state_calls = []
        self.ocr_init_thread = None

    def _set_runtime_state(self, state):
        self.state_calls.append(state)


def test_start_ocr_initialization_runs_real_initializer_on_thread_factory():
    app = FakeApp(ready=True)

    start_ocr_initialization(
        app,
        thread_factory=ImmediateThread,
        fast_ocr_enabled=lambda: False,
    )

    assert app.ocr_initializing is True
    assert app.state_calls == [RuntimeState.OCR_LOADING]
    assert app.ocr_workflow_manager.initialize_calls == 1
    assert app.ocr_workflow_manager.ocr_reader is not None
    assert app.message_queue.get_nowait() == ("ocr_ready", True)
    assert isinstance(app.ocr_init_thread, ImmediateThread)
    assert app.ocr_init_thread.daemon is True


def test_start_ocr_initialization_reports_failure_when_reader_missing():
    app = FakeApp(ready=False)

    start_ocr_initialization(
        app,
        thread_factory=ImmediateThread,
        fast_ocr_enabled=lambda: False,
    )

    assert app.ocr_workflow_manager.initialize_calls == 1
    assert app.message_queue.get_nowait() == ("ocr_ready", False)


def test_start_ocr_initialization_fast_smoke_sets_reader_without_thread():
    app = FakeApp(ready=False)

    start_ocr_initialization(
        app,
        thread_factory=ImmediateThread,
        fast_ocr_enabled=lambda: True,
    )

    assert app.ocr_workflow_manager.initialize_calls == 0
    assert app.ocr_workflow_manager.ocr_reader is not None
    assert app.ocr_init_thread is None
    assert app.message_queue.get_nowait() == ("ocr_ready", True)


def test_start_ocr_initialization_noops_when_already_initializing_or_ready():
    initializing_app = FakeApp(ready=True)
    initializing_app.ocr_initializing = True
    ready_app = FakeApp(ready=True)
    ready_app.ocr_workflow_manager.ocr_reader = object()

    start_ocr_initialization(initializing_app, thread_factory=ImmediateThread)
    start_ocr_initialization(ready_app, thread_factory=ImmediateThread)

    assert initializing_app.state_calls == []
    assert initializing_app.ocr_workflow_manager.initialize_calls == 0
    assert ready_app.state_calls == []
    assert ready_app.ocr_workflow_manager.initialize_calls == 0
