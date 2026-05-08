from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui.panels import preset_panel


class FakeWidget:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.insert_calls = []
        self.__class__.created.append(self)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def insert(self, index, value):
        self.insert_calls.append((index, value))


class FakeFrame(FakeWidget):
    created = []


class FakeLabel(FakeWidget):
    created = []


class FakeButton(FakeWidget):
    created = []


class FakeEntry(FakeWidget):
    created = []


class FakeCombobox(FakeWidget):
    created = []


class FakeThemeManager:
    def __init__(self):
        self.registered = []

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))


class FakeApp:
    def __init__(self):
        self.theme_manager = FakeThemeManager()
        self.sections = []
        self.preset_combo = None
        self.preset_name_entry = None
        self.updated_presets = 0

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        section = FakeFrame(parent, title=title, fill_parent=fill_parent)
        self.sections.append((parent, title, fill_parent, section))
        return section

    def apply_selected_preset(self):
        raise AssertionError("construction must not apply presets")

    def delete_selected_preset(self):
        raise AssertionError("construction must not delete presets")

    def save_current_as_preset(self):
        raise AssertionError("construction must not save presets")

    def update_preset_combo(self):
        self.updated_presets += 1


def test_create_preset_panel_builds_combo_entry_and_commands(monkeypatch):
    for widget_class in (FakeFrame, FakeLabel, FakeButton, FakeEntry, FakeCombobox):
        widget_class.created = []
    fake_tk = SimpleNamespace(
        Frame=FakeFrame,
        Label=FakeLabel,
        Button=FakeButton,
        Entry=FakeEntry,
    )
    fake_ttk = SimpleNamespace(Combobox=FakeCombobox)
    monkeypatch.setattr(preset_panel, "tk", fake_tk)
    monkeypatch.setattr(preset_panel, "ttk", fake_ttk)
    app = FakeApp()
    parent = object()

    preset_panel.create_preset_panel(app, parent)

    assert app.sections[0][0:3] == (parent, "💾 프리셋 관리", True)
    assert app.updated_presets == 1
    assert app.preset_combo.kwargs["state"] == "readonly"
    assert app.preset_combo.kwargs["style"] == "TCombobox"
    assert app.preset_combo.pack_calls[-1] == {
        "side": "left",
        "fill": "x",
        "expand": True,
        "padx": (0, 5),
    }

    assert [label.kwargs["text"] for label in FakeLabel.created] == [
        "저장된 프리셋:",
        "새 프리셋 저장:",
    ]
    assert [button.kwargs["text"] for button in FakeButton.created] == ["적용", "삭제", "저장"]
    assert [button.kwargs["command"] for button in FakeButton.created] == [
        app.apply_selected_preset,
        app.delete_selected_preset,
        app.save_current_as_preset,
    ]
    assert app.preset_name_entry.kwargs["relief"] == "solid"
    assert app.preset_name_entry.kwargs["bd"] == 1
    assert app.preset_name_entry.insert_calls == [(0, "새 프리셋 이름")]
    assert app.preset_name_entry.pack_calls[-1] == {
        "side": "left",
        "fill": "x",
        "expand": True,
        "padx": (0, 5),
    }

    registered_styles = [style for _widget, style in app.theme_manager.registered]
    assert {"bg": "success", "fg": "white", "activebackground": "dark"} in registered_styles
    assert {"bg": "danger", "fg": "white", "activebackground": "dark"} in registered_styles
    assert {"bg": "accent", "fg": "white", "activebackground": "dark"} in registered_styles
