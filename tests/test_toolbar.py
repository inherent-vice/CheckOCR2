from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui import toolbar


class FakeWidget:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.grid_calls = []
        self.pack_propagate_calls = []
        self.__class__.created.append(self)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def grid(self, **kwargs):
        self.grid_calls.append(kwargs)

    def pack_propagate(self, value):
        self.pack_propagate_calls.append(value)


class FakeFrame(FakeWidget):
    created = []


class FakeLabel(FakeWidget):
    created = []


class FakeButton(FakeWidget):
    created = []


class FakeCombobox(FakeWidget):
    created = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = {}
        self.set_calls = []
        self.bind_calls = []

    def __setitem__(self, key, value):
        self.items[key] = value

    def set(self, value):
        self.set_calls.append(value)

    def bind(self, sequence, callback):
        self.bind_calls.append((sequence, callback))


class FakeThemeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeThemeManager:
    def __init__(self):
        self.available_themes = {
            "blue": {"name": "Blue"},
            "green": {"name": "Green"},
        }
        self.current_theme_key = "blue"
        self.registered = []
        self.changed_to = None

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))

    def change_theme(self, theme_key):
        self.changed_to = theme_key


class FakeApp:
    def __init__(self):
        self.theme_manager = FakeThemeManager()
        self.theme_var = FakeThemeVar("Green")
        self.run_btn = None
        self.stop_btn = None
        self.theme_combo = None

    def run_ocr_process(self):
        raise AssertionError("construction must not start OCR")

    def stop_processing_ui_initiated(self):
        raise AssertionError("construction must not stop OCR")


def test_create_simple_toolbar_builds_runtime_controls_and_theme_combo(monkeypatch):
    for widget_class in (FakeFrame, FakeLabel, FakeButton, FakeCombobox):
        widget_class.created = []
    fake_tk = SimpleNamespace(Frame=FakeFrame, Label=FakeLabel, Button=FakeButton)
    fake_ttk = SimpleNamespace(Combobox=FakeCombobox)
    monkeypatch.setattr(toolbar, "tk", fake_tk)
    monkeypatch.setattr(toolbar, "ttk", fake_ttk)
    app = FakeApp()

    toolbar.create_simple_toolbar(app)

    root_toolbar = FakeFrame.created[0]
    assert root_toolbar.kwargs["height"] == 35
    assert root_toolbar.grid_calls[-1] == {"row": 0, "column": 0, "sticky": "ew", "padx": 0, "pady": 0}
    assert root_toolbar.pack_propagate_calls == [False]
    assert FakeLabel.created[0].kwargs["text"] == "📊 Check Capture OCR V6.1"

    assert [button.kwargs["text"] for button in FakeButton.created] == [
        "🚀 OCR 시작 (F5)",
        "⏹️ 중단",
    ]
    assert [button.kwargs["command"] for button in FakeButton.created] == [
        app.run_ocr_process,
        app.stop_processing_ui_initiated,
    ]
    assert app.run_btn is FakeButton.created[0]
    assert app.stop_btn is FakeButton.created[1]

    assert app.theme_combo is FakeCombobox.created[0]
    assert app.theme_combo.kwargs["textvariable"] is app.theme_var
    assert app.theme_combo.kwargs["state"] == "readonly"
    assert app.theme_combo.items["values"] == ["Blue", "Green"]
    assert app.theme_combo.set_calls == ["Blue"]
    assert app.theme_combo.bind_calls[0][0] == "<<ComboboxSelected>>"

    app.theme_combo.bind_calls[0][1](None)
    assert app.theme_manager.changed_to == "green"
