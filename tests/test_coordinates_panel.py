from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui.panels import coordinates_panel


class FakeWidget:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.grid_calls = []
        self.grid_columnconfigure_calls = []
        self.__class__.created.append(self)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def grid(self, **kwargs):
        self.grid_calls.append(kwargs)

    def grid_columnconfigure(self, index, **kwargs):
        self.grid_columnconfigure_calls.append((index, kwargs))


class FakeFrame(FakeWidget):
    created = []


class FakeButton(FakeWidget):
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

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        section = FakeFrame(parent, title=title, fill_parent=fill_parent)
        self.sections.append((parent, title, fill_parent, section))
        return section

    def relocate_clickpoint(self):
        raise AssertionError("construction must not relocate click point")

    def relocate_allarea(self):
        raise AssertionError("construction must not relocate all area")

    def relocate_datearea(self):
        raise AssertionError("construction must not relocate date area")

    def relocate_ratearea(self):
        raise AssertionError("construction must not relocate rate area")

    def show_area_preview(self):
        raise AssertionError("construction must not open preview")


def test_create_coordinates_panel_builds_area_buttons(monkeypatch):
    for widget_class in (FakeFrame, FakeButton):
        widget_class.created = []
    fake_tk = SimpleNamespace(Frame=FakeFrame, Button=FakeButton)
    monkeypatch.setattr(coordinates_panel, "tk", fake_tk)
    app = FakeApp()
    parent = object()

    coordinates_panel.create_coordinates_panel(app, parent)

    assert app.sections[0][0:3] == (parent, "🎯 좌표 및 영역 설정", False)
    grid_container = FakeFrame.created[1]
    assert grid_container.pack_calls[-1] == {"fill": "x", "pady": (0, 5)}
    assert grid_container.grid_columnconfigure_calls == [
        (0, {"weight": 1}),
        (1, {"weight": 1}),
    ]

    assert [button.kwargs["text"] for button in FakeButton.created] == [
        "🎯 클릭 포인트",
        "🔍 전체 영역",
        "🔍 날짜 영역",
        "🔍 금리 영역",
        "🔍 전체 영역 미리보기",
    ]
    assert [button.kwargs["command"] for button in FakeButton.created] == [
        app.relocate_clickpoint,
        app.relocate_allarea,
        app.relocate_datearea,
        app.relocate_ratearea,
        app.show_area_preview,
    ]
    assert FakeButton.created[0].grid_calls[-1] == {
        "row": 0,
        "column": 0,
        "sticky": "nsew",
        "padx": (0, 2),
        "pady": (0, 2),
    }
    assert FakeButton.created[4].pack_calls[-1] == {"fill": "x", "pady": (8, 0)}

    registered_styles = [style for _widget, style in app.theme_manager.registered]
    assert {"bg": "accent", "fg": "white", "activebackground": "dark"} in registered_styles
    assert {"bg": "warning", "fg": "white", "activebackground": "dark"} in registered_styles
