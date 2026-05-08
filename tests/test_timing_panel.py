from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui.panels import timing_panel


class FakeWidget:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.__class__.created.append(self)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)


class FakeFrame(FakeWidget):
    created = []


class FakeLabel(FakeWidget):
    created = []


class FakeEntry(FakeWidget):
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
        self.paste_delay = object()
        self.loading_delay = object()

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        section = FakeFrame(parent, title=title, fill_parent=fill_parent)
        self.sections.append((parent, title, fill_parent, section))
        return section


def test_create_timing_panel_builds_delay_entries(monkeypatch):
    for widget_class in (FakeFrame, FakeLabel, FakeEntry):
        widget_class.created = []
    fake_tk = SimpleNamespace(Frame=FakeFrame, Label=FakeLabel, Entry=FakeEntry)
    monkeypatch.setattr(timing_panel, "tk", fake_tk)
    app = FakeApp()
    parent = object()

    timing_panel.create_timing_panel(app, parent)

    assert app.sections[0][0:3] == (parent, "⏱️ 타이밍 설정", False)
    assert [label.kwargs["text"] for label in FakeLabel.created] == [
        "붙여넣기 딜레이(초):",
        "로딩 딜레이(초):",
    ]
    assert [entry.kwargs["textvariable"] for entry in FakeEntry.created] == [
        app.paste_delay,
        app.loading_delay,
    ]
    assert all(entry.kwargs["width"] == 10 for entry in FakeEntry.created)
    assert FakeFrame.created[2].pack_calls[-1] == {
        "side": "left",
        "fill": "x",
        "expand": True,
        "padx": (0, 5),
    }
    assert FakeFrame.created[3].pack_calls[-1] == {
        "side": "left",
        "fill": "x",
        "expand": True,
        "padx": (5, 0),
    }
    assert app.theme_manager.registered[0][1] == {"bg": "white"}
