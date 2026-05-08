from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui.panels import log_panel


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.configure_calls = []

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)


class FakeText(FakeWidget):
    def yview(self, *args, **kwargs):
        return None


class FakeScrollbar(FakeWidget):
    def set(self, *args, **kwargs):
        return None


class FakeThemeManager:
    def __init__(self):
        self.registered = []

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))


class FakeApp:
    def __init__(self):
        self.theme_manager = FakeThemeManager()
        self.sections = []

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        section = FakeWidget(parent, title=title, fill_parent=fill_parent)
        self.sections.append((parent, title, fill_parent, section))
        return section


def test_create_log_panel_builds_disabled_text_with_scrollbar(monkeypatch):
    fake_tk = SimpleNamespace(Frame=FakeWidget, Text=FakeText)
    fake_ttk = SimpleNamespace(Scrollbar=FakeScrollbar)
    monkeypatch.setattr(log_panel, "tk", fake_tk)
    monkeypatch.setattr(log_panel, "ttk", fake_ttk)
    app = FakeApp()
    parent = object()

    text_widget = log_panel.create_log_panel(app, parent)

    assert isinstance(text_widget, FakeText)
    assert app.sections[0][0:3] == (parent, "📊 상태 및 로그", True)
    assert text_widget.kwargs["state"] == "disabled"
    assert text_widget.kwargs["wrap"] == "word"
    assert text_widget.kwargs["width"] == 20
    assert text_widget.configure_calls
    assert text_widget.pack_calls[-1] == {"side": "left", "fill": "both", "expand": True}
    assert app.theme_manager.registered[0][1] == {"bg": "white"}
    assert app.theme_manager.registered[1][1] == {
        "bg": "white",
        "fg": "on_surface",
        "insertbackground": "on_surface",
    }
