from __future__ import annotations

from pathlib import Path

from checkocr2.package_smoke_status import PACKAGE_SMOKE_STATUS_FILE_ENV
from checkocr2.runtime_state import RuntimeState, runtime_state_ui
from checkocr2.ui import runtime_status_actions


class FakeButton:
    def __init__(self):
        self.config_calls = []

    def config(self, **kwargs):
        self.config_calls.append(kwargs)

    @property
    def last_config(self):
        return self.config_calls[-1]


class FakeLogger:
    def __init__(self):
        self.debugs = []

    def debug(self, message, *args):
        self.debugs.append((message, args))


class FakeWorkflow:
    def __init__(self, reader=None):
        self.ocr_reader = reader


class FakeSettingsManager:
    def __init__(self, settings_file):
        self.settings_file = settings_file


class FakeApp:
    def __init__(self, *, reader=None):
        self.runtime_state = RuntimeState.STARTING
        self.run_btn = FakeButton()
        self.stop_btn = FakeButton()
        self.ocr_workflow_manager = FakeWorkflow(reader=reader)
        self.settings_manager = FakeSettingsManager(Path("settings.json"))
        self.logger = FakeLogger()
        self.state_calls = []

    def _set_runtime_state(self, state):
        self.state_calls.append(state)


def test_set_runtime_state_updates_buttons_and_writes_package_status(monkeypatch):
    app = FakeApp(reader=object())
    written = []
    monkeypatch.setenv(PACKAGE_SMOKE_STATUS_FILE_ENV, "status.json")
    monkeypatch.setattr(
        runtime_status_actions,
        "write_package_smoke_status",
        lambda status_file, **kwargs: written.append((status_file, kwargs)),
    )

    runtime_status_actions.set_runtime_state(app, RuntimeState.RUNNING)

    ui_state = runtime_state_ui(RuntimeState.RUNNING)
    assert app.runtime_state is RuntimeState.RUNNING
    assert app.run_btn.last_config == {
        "state": ui_state.run_button_state,
        "text": ui_state.run_button_text,
    }
    assert app.stop_btn.last_config == {"state": ui_state.stop_button_state}
    assert written == [
        (
            "status.json",
            {
                "runtime_state": RuntimeState.RUNNING,
                "ocr_ready": True,
                "settings_file": Path("settings.json"),
            },
        )
    ]


def test_set_runtime_state_without_run_button_still_writes_package_status(monkeypatch):
    app = FakeApp(reader=None)
    app.run_btn = None
    written = []
    monkeypatch.setenv(PACKAGE_SMOKE_STATUS_FILE_ENV, "status.json")
    monkeypatch.setattr(
        runtime_status_actions,
        "write_package_smoke_status",
        lambda status_file, **kwargs: written.append((status_file, kwargs)),
    )

    runtime_status_actions.set_runtime_state(app, RuntimeState.OCR_LOADING)

    assert app.runtime_state is RuntimeState.OCR_LOADING
    assert app.stop_btn.config_calls == []
    assert written[0][1]["runtime_state"] is RuntimeState.OCR_LOADING
    assert written[0][1]["ocr_ready"] is False


def test_set_runtime_state_without_smoke_env_does_not_require_workflow_manager(monkeypatch):
    app = FakeApp(reader=None)
    del app.ocr_workflow_manager
    monkeypatch.delenv(PACKAGE_SMOKE_STATUS_FILE_ENV, raising=False)

    runtime_status_actions.set_runtime_state(app, RuntimeState.READY)

    ready_ui = runtime_state_ui(RuntimeState.READY)
    assert app.runtime_state is RuntimeState.READY
    assert app.run_btn.last_config == {
        "state": ready_ui.run_button_state,
        "text": ready_ui.run_button_text,
    }
    assert app.stop_btn.last_config == {"state": ready_ui.stop_button_state}


def test_set_ocr_ready_ui_delegates_to_legacy_runtime_state_wrapper():
    app = FakeApp()

    runtime_status_actions.set_ocr_ready_ui(app, True)
    runtime_status_actions.set_ocr_ready_ui(app, False)

    assert app.state_calls == [RuntimeState.READY, RuntimeState.OCR_LOADING]


def test_ready_or_error_state_reflects_reader_presence():
    assert runtime_status_actions.ready_or_error_state(FakeApp(reader=object())) is RuntimeState.READY
    assert runtime_status_actions.ready_or_error_state(FakeApp(reader=None)) is RuntimeState.ERROR


def test_write_package_smoke_status_for_app_ignores_missing_env(monkeypatch):
    app = FakeApp(reader=object())
    monkeypatch.delenv(PACKAGE_SMOKE_STATUS_FILE_ENV, raising=False)

    assert runtime_status_actions.write_package_smoke_status_for_app(app) is None


def test_write_package_smoke_status_for_app_logs_write_failures(monkeypatch):
    app = FakeApp(reader=object())
    monkeypatch.setenv(PACKAGE_SMOKE_STATUS_FILE_ENV, "status.json")

    def failing_writer(*args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(runtime_status_actions, "write_package_smoke_status", failing_writer)

    assert runtime_status_actions.write_package_smoke_status_for_app(app) is None
    assert app.logger.debugs[0][0] == "Package smoke status write failed: %s"
    assert isinstance(app.logger.debugs[0][1][0], OSError)
    assert str(app.logger.debugs[0][1][0]) == "denied"


def test_legacy_app_runtime_status_methods_delegate(ocr_module, monkeypatch):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "set_runtime_state_action",
        lambda actual_app, state: calls.append(("set", actual_app, state)),
    )
    monkeypatch.setattr(
        ocr_module,
        "set_ocr_ready_ui_action",
        lambda actual_app, ready: calls.append(("ready", actual_app, ready)),
    )
    monkeypatch.setattr(
        ocr_module,
        "ready_or_error_state_action",
        lambda actual_app: calls.append(("state", actual_app)) or RuntimeState.ERROR,
    )
    monkeypatch.setattr(
        ocr_module,
        "write_package_smoke_status_action",
        lambda actual_app: calls.append(("write", actual_app)),
    )

    app._set_runtime_state(RuntimeState.READY)
    app._set_ocr_ready_ui(False)
    state = app._ready_or_error_state()
    app._write_package_smoke_status()

    assert state is RuntimeState.ERROR
    assert calls == [
        ("set", app, RuntimeState.READY),
        ("ready", app, False),
        ("state", app),
        ("write", app),
    ]
