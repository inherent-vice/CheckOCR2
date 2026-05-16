from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui.panels import file_panel


class FakeWidget:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.configure_calls = []
        self.__class__.created.append(self)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)


class FakeFrame(FakeWidget):
    created = []


class FakeLabel(FakeWidget):
    created = []


class FakeEntry(FakeWidget):
    created = []


class FakeButton(FakeWidget):
    created = []

    def bind(self, sequence, func, add=None):
        pass


class FakeThemeManager:
    def __init__(self):
        self.registered = []

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))


class FakeApp:
    def __init__(self):
        self.theme_manager = FakeThemeManager()
        self.sections = []
        self.input_excel_path = object()
        self.output_folder_path = object()
        self.excel_entry = None
        self.output_entry = None
        self.open_folder_btn = None

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        section = FakeFrame(parent, title=title, fill_parent=fill_parent)
        self.sections.append((parent, title, fill_parent, section))
        return section

    def browse_input_excel(self):
        raise AssertionError("construction must not open file dialog")

    def browse_output_folder(self):
        raise AssertionError("construction must not open folder dialog")

    def open_output_folder(self):
        raise AssertionError("construction must not open output folder")


def test_create_file_panel_builds_entries_and_commands(monkeypatch):
    for widget_class in (FakeFrame, FakeLabel, FakeEntry, FakeButton):
        widget_class.created = []
    fake_tk = SimpleNamespace(Frame=FakeFrame, Label=FakeLabel, Entry=FakeEntry, Button=FakeButton)
    monkeypatch.setattr(file_panel, "tk", fake_tk)
    app = FakeApp()
    parent = object()

    file_panel.create_file_panel(app, parent)

    assert app.sections[0][0:3] == (parent, "📁 파일 설정", False)
    assert app.excel_entry.kwargs["textvariable"] is app.input_excel_path
    assert app.output_entry.kwargs["textvariable"] is app.output_folder_path
    assert app.open_folder_btn.kwargs["command"] == app.open_output_folder

    commands = [button.kwargs["command"] for button in FakeButton.created]
    assert commands == [app.browse_input_excel, app.browse_output_folder, app.open_output_folder]
    assert [button.kwargs["text"] for button in FakeButton.created] == ["찾기", "찾기", "📂"]
    assert app.excel_entry.pack_calls[-1] == {"side": "left", "fill": "x", "expand": True, "padx": (0, 5)}
    assert app.output_entry.pack_calls[-1] == {"side": "left", "fill": "x", "expand": True, "padx": (0, 5)}
    assert app.open_folder_btn.pack_calls[-1] == {"side": "left", "padx": (5, 0)}
    assert ("bg", "white") in [(key, value) for _widget, style in app.theme_manager.registered for key, value in style.items()]
