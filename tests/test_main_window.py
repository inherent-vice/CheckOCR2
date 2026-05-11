from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui import main_window


class FakeFrame:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.grid_calls = []
        self.pack_calls = []
        self.grid_rowconfigure_calls = []
        self.grid_columnconfigure_calls = []
        self.__class__.created.append(self)

    def grid(self, **kwargs):
        self.grid_calls.append(kwargs)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def grid_rowconfigure(self, index, **kwargs):
        self.grid_rowconfigure_calls.append((index, kwargs))

    def grid_columnconfigure(self, index, **kwargs):
        self.grid_columnconfigure_calls.append((index, kwargs))


class FakeThemeManager:
    def __init__(self):
        self.registered = []

    def get_color(self, color_key, default=None):
        return f"{color_key}-color"

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))


class FakeLogger:
    def __init__(self):
        self.handlers = []

    def addHandler(self, handler):
        self.handlers.append(handler)


class FakeHandler:
    def __init__(self, widget, message_queue):
        self.widget = widget
        self.message_queue = message_queue


class FakeApp:
    def __init__(self):
        self.theme_manager = FakeThemeManager()
        self.message_queue = object()
        self.logger = FakeLogger()
        self.log_text_widget = None
        self.configure_calls = []
        self.grid_rowconfigure_calls = []
        self.grid_columnconfigure_calls = []
        self.calls = []

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def grid_rowconfigure(self, index, **kwargs):
        self.grid_rowconfigure_calls.append((index, kwargs))

    def grid_columnconfigure(self, index, **kwargs):
        self.grid_columnconfigure_calls.append((index, kwargs))

    def _create_menu(self):
        self.calls.append(("menu", None))

    def _create_simple_toolbar(self):
        self.calls.append(("toolbar", None))

    def _create_left_panel_content(self, parent):
        self.calls.append(("left", parent))

    def _create_center_excel_grid(self, parent):
        self.calls.append(("center", parent))

    def _create_right_panel_content(self, parent):
        self.calls.append(("right", parent))
        self.log_text_widget = object()

    def _create_file_section(self, parent):
        self.calls.append(("file", parent))

    def _create_coordinates_section(self, parent):
        self.calls.append(("coordinates", parent))

    def _create_timing_section(self, parent):
        self.calls.append(("timing", parent))

    def _create_options_section(self, parent):
        self.calls.append(("options", parent))

    def _create_preset_section(self, parent):
        self.calls.append(("preset", parent))


def test_build_main_window_assembles_three_panel_layout_and_log_handler(monkeypatch):
    FakeFrame.created = []
    monkeypatch.setattr(main_window, "tk", SimpleNamespace(Frame=FakeFrame))
    monkeypatch.setattr(main_window, "TkinterLogHandler", FakeHandler)
    app = FakeApp()

    main_window.build_main_window(app)

    assert app.configure_calls == [{"bg": "surface-color"}]
    assert app.grid_rowconfigure_calls == [(0, {"weight": 0}), (1, {"weight": 1})]
    assert app.grid_columnconfigure_calls == [(0, {"weight": 1})]

    main_container, left_panel, center_panel, right_panel = FakeFrame.created
    assert main_container.args == (app,)
    assert main_container.grid_calls == [
        {"row": 1, "column": 0, "sticky": "nsew", "padx": 0, "pady": 0}
    ]
    assert main_container.grid_rowconfigure_calls == [(0, {"weight": 1})]
    assert main_container.grid_columnconfigure_calls == [
        (0, {"weight": 0, "minsize": 280}),
        (1, {"weight": 6}),
        (2, {"weight": 1, "minsize": 200}),
    ]
    assert left_panel.grid_calls[-1] == {
        "row": 0,
        "column": 0,
        "sticky": "nsew",
        "padx": (5, 2),
        "pady": 5,
    }
    assert center_panel.grid_calls[-1] == {
        "row": 0,
        "column": 1,
        "sticky": "nsew",
        "padx": 3,
        "pady": 5,
    }
    assert right_panel.grid_calls[-1] == {
        "row": 0,
        "column": 2,
        "sticky": "nsew",
        "padx": (2, 5),
        "pady": 5,
    }
    assert app.calls == [
        ("menu", None),
        ("toolbar", None),
        ("left", left_panel),
        ("center", center_panel),
        ("right", right_panel),
    ]
    assert app.logger.handlers[0].widget is app.log_text_widget
    assert app.logger.handlers[0].message_queue is app.message_queue


def test_create_left_panel_content_builds_scrollable_frame_and_sections(monkeypatch):
    FakeFrame.created = []
    monkeypatch.setattr(main_window, "tk", SimpleNamespace(Frame=FakeFrame))
    app = FakeApp()
    parent = object()

    main_window.create_left_panel_content(app, parent)

    scrollable_frame = FakeFrame.created[0]
    assert scrollable_frame.args == (parent,)
    assert scrollable_frame.pack_calls == [
        {"fill": "both", "expand": True, "padx": 0, "pady": 0}
    ]
    assert app.calls == [
        ("file", scrollable_frame),
        ("coordinates", scrollable_frame),
        ("timing", scrollable_frame),
        ("options", scrollable_frame),
        ("preset", scrollable_frame),
    ]


def test_create_right_panel_content_sets_log_widget(monkeypatch):
    app = FakeApp()
    parent = object()
    log_widget = object()
    monkeypatch.setattr(main_window, "create_log_panel", lambda app, parent: log_widget)

    main_window.create_right_panel_content(app, parent)

    assert app.log_text_widget is log_widget
