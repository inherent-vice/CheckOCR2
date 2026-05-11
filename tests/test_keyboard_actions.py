from __future__ import annotations

from checkocr2.ui import keyboard_actions


class FakeWorkController:
    def __init__(self, *, running=False):
        self.is_running = running


class FakeApp:
    def __init__(self, *, running=False):
        self.focused = False
        self.bindings = {}
        self.actions = []
        self.work_controller = FakeWorkController(running=running)

    def focus_set(self):
        self.focused = True

    def bind_all(self, sequence, callback):
        self.bindings[sequence] = callback

    def quick_save_settings(self):
        self.actions.append("quick_save")

    def load_last_settings(self):
        self.actions.append("load_last")

    def load_excel_to_grid(self):
        self.actions.append("load_excel")

    def handle_f5_key(self):
        self.actions.append("f5")

    def stop_processing_ui_initiated(self):
        self.actions.append("stop")

    def show_shortcuts(self):
        self.actions.append("shortcuts")

    def run_ocr_process(self):
        self.actions.append("run")


def test_setup_keyboard_shortcuts_preserves_legacy_bindings_and_callbacks():
    app = FakeApp()

    keyboard_actions.setup_keyboard_shortcuts(app)

    assert app.focused is True
    assert list(app.bindings) == [
        "<Control-s>",
        "<Control-l>",
        "<Control-o>",
        "<F5>",
        "<Escape>",
        "<F1>",
    ]

    for sequence in app.bindings:
        app.bindings[sequence](object())

    assert app.actions == ["quick_save", "load_last", "load_excel", "f5", "stop", "shortcuts"]


def test_handle_f5_key_runs_when_idle_and_stops_when_running():
    idle_app = FakeApp(running=False)
    running_app = FakeApp(running=True)

    keyboard_actions.handle_f5_key(idle_app)
    keyboard_actions.handle_f5_key(running_app)

    assert idle_app.actions == ["run"]
    assert running_app.actions == ["stop"]


def test_legacy_app_keyboard_methods_delegate(ocr_module, monkeypatch):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(ocr_module, "setup_keyboard_shortcuts", lambda actual_app: calls.append(("setup", actual_app)))
    monkeypatch.setattr(ocr_module, "handle_f5_key_action", lambda actual_app: calls.append(("f5", actual_app)))

    app._setup_keyboard_shortcuts()
    app.handle_f5_key()

    assert calls == [("setup", app), ("f5", app)]
