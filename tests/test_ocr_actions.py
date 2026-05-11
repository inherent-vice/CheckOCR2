from __future__ import annotations

import queue
from types import SimpleNamespace

from checkocr2.runtime_state import RuntimeState
from checkocr2.ui import ocr_actions


class FakeWorkController:
    def __init__(self, *, running=False):
        self.is_running = running
        self.started = 0
        self.stopped = 0

    def start_work(self):
        self.started += 1
        self.is_running = True

    def stop_work(self):
        self.stopped += 1
        self.is_running = False
        return "stopped"


class FakeWorkflow:
    def __init__(self):
        self.calls = []

    def execute_ocr_workflow_threaded(self, *args):
        self.calls.append(args)


class FakeApp:
    def __init__(self, *, running=False, valid=True):
        self.work_controller = FakeWorkController(running=running)
        self.ocr_workflow_manager = FakeWorkflow()
        self.message_queue = queue.Queue()
        self.output_folder_path = SimpleNamespace(get=lambda: "  C:/Output  ")
        self.save_detail_images = SimpleNamespace(get=lambda: True)
        self.worker_thread = None
        self.runtime_states = []
        self.valid = valid
        self.current_settings = {"click_point": (1, 2)}
        self.stop_ui_calls = 0

    def _set_runtime_state(self, state):
        self.runtime_states.append(state)

    def _validate_inputs_for_ocr(self):
        return self.valid

    def get_current_ui_settings(self):
        return self.current_settings

    def stop_processing_ui_initiated(self):
        self.stop_ui_calls += 1


def test_run_ocr_process_starts_worker_with_current_ui_contract():
    app = FakeApp(valid=True)
    worker_calls = []

    def start_worker(target, *args, **kwargs):
        worker_calls.append((target, args, kwargs))
        return "worker-handle"

    ocr_actions.run_ocr_process(app, start_worker=start_worker)

    assert app.work_controller.started == 1
    assert app.runtime_states == [RuntimeState.RUNNING]
    assert app.worker_thread == "worker-handle"
    assert worker_calls == [
        (
            app.ocr_workflow_manager.execute_ocr_workflow_threaded,
            ({"click_point": (1, 2)}, "C:/Output", True),
            {"name": "checkocr2-ocr-workflow"},
        )
    ]


def test_run_ocr_process_stops_instead_of_starting_when_already_running():
    app = FakeApp(running=True)
    worker_calls = []

    ocr_actions.run_ocr_process(
        app,
        start_worker=lambda *args, **kwargs: worker_calls.append((args, kwargs)),
    )

    assert app.stop_ui_calls == 1
    assert app.work_controller.started == 0
    assert worker_calls == []


def test_run_ocr_process_does_not_start_worker_when_validation_fails():
    app = FakeApp(valid=False)

    ocr_actions.run_ocr_process(
        app,
        start_worker=lambda *args, **kwargs: "unexpected",
    )

    assert app.work_controller.started == 0
    assert app.worker_thread is None
    assert app.runtime_states == []


def test_stop_processing_updates_state_and_queues_log_only_when_running():
    app = FakeApp(running=True)

    ocr_actions.stop_processing(app)

    assert app.work_controller.stopped == 1
    assert app.runtime_states == [RuntimeState.STOPPING]
    assert app.message_queue.get_nowait() == ("log", "stopped", "INFO")

    ocr_actions.stop_processing(app)

    assert app.message_queue.empty()


def test_legacy_app_ocr_action_methods_delegate(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "run_ocr_process_action",
        lambda app_ref: calls.append(("run", app_ref)),
    )
    monkeypatch.setattr(
        ocr_module,
        "stop_processing_action",
        lambda app_ref: calls.append(("stop", app_ref)),
    )

    app.run_ocr_process()
    app.stop_processing_ui_initiated()

    assert calls == [("run", app), ("stop", app)]
