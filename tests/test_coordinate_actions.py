from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui import coordinate_actions
from checkocr2.ui.overlays import close_overlay_on_escape


class FakeVar:
    def __init__(self, value=0):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeApp:
    def __init__(self):
        self.theme_manager = object()
        self.waited = []
        self.click_x = FakeVar(10)
        self.click_y = FakeVar(20)
        self.allarea_x1 = FakeVar(1)
        self.allarea_y1 = FakeVar(2)
        self.allarea_x2 = FakeVar(3)
        self.allarea_y2 = FakeVar(4)
        self.datearea_x1 = FakeVar(5)
        self.datearea_y1 = FakeVar(6)
        self.datearea_x2 = FakeVar(7)
        self.datearea_y2 = FakeVar(8)
        self.ratearea_x1 = FakeVar(9)
        self.ratearea_y1 = FakeVar(10)
        self.ratearea_x2 = FakeVar(11)
        self.ratearea_y2 = FakeVar(12)

    def wait_window(self, overlay):
        self.waited.append(overlay)


def test_relocate_clickpoint_updates_vars_when_overlay_returns_point():
    app = FakeApp()

    def overlay_factory(parent, *, color_key, theme_manager):
        assert parent is app
        assert color_key == "danger"
        assert theme_manager is app.theme_manager
        return SimpleNamespace(click_x=111, click_y=222)

    coordinate_actions.relocate_clickpoint(app, point_overlay_factory=overlay_factory)

    assert app.waited
    assert (app.click_x.get(), app.click_y.get()) == (111, 222)


def test_relocate_clickpoint_keeps_vars_when_cancelled():
    app = FakeApp()

    coordinate_actions.relocate_clickpoint(
        app,
        point_overlay_factory=lambda *args, **kwargs: SimpleNamespace(click_x=None, click_y=None),
    )

    assert (app.click_x.get(), app.click_y.get()) == (10, 20)


def test_relocate_area_updates_all_four_vars_when_overlay_returns_area():
    app = FakeApp()

    def overlay_factory(parent, *, color_key, theme_manager):
        assert parent is app
        assert color_key == "success"
        assert theme_manager is app.theme_manager
        return SimpleNamespace(x1=100, y1=200, x2=300, y2=400)

    coordinate_actions.relocate_area(
        app,
        app.datearea_x1,
        app.datearea_y1,
        app.datearea_x2,
        app.datearea_y2,
        "success",
        drag_overlay_factory=overlay_factory,
    )

    assert (app.datearea_x1.get(), app.datearea_y1.get()) == (100, 200)
    assert (app.datearea_x2.get(), app.datearea_y2.get()) == (300, 400)


def test_relocate_area_keeps_vars_when_cancelled():
    app = FakeApp()

    coordinate_actions.relocate_area(
        app,
        app.allarea_x1,
        app.allarea_y1,
        app.allarea_x2,
        app.allarea_y2,
        "primary",
        drag_overlay_factory=lambda *args, **kwargs: SimpleNamespace(x1=None, y1=None, x2=None, y2=None),
    )

    assert (app.allarea_x1.get(), app.allarea_y1.get()) == (1, 2)
    assert (app.allarea_x2.get(), app.allarea_y2.get()) == (3, 4)


def test_show_area_preview_passes_current_areas_to_overlay():
    app = FakeApp()
    created = []

    def preview_factory(parent, areas_info, theme_manager, *, auto_close):
        created.append((parent, areas_info, theme_manager, auto_close))

    coordinate_actions.show_area_preview(app, preview_overlay_factory=preview_factory)

    assert created == [
        (
            app,
            {
                "click_point": (10, 20),
                "all_area": (1, 2, 3, 4),
                "date_area": (5, 6, 7, 8),
                "rate_area": (9, 10, 11, 12),
            },
            app.theme_manager,
            True,
        )
    ]


def test_close_overlay_on_escape_destroys_only_for_escape_key():
    destroyed = []
    window = SimpleNamespace(destroy=lambda: destroyed.append(True))

    assert close_overlay_on_escape(window, SimpleNamespace(keysym="Return")) is None
    assert destroyed == []

    assert close_overlay_on_escape(window, SimpleNamespace(keysym="Escape")) == "break"
    assert destroyed == [True]


def test_legacy_app_coordinate_methods_delegate(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    app.allarea_x1 = object()
    app.allarea_y1 = object()
    app.allarea_x2 = object()
    app.allarea_y2 = object()
    app.datearea_x1 = object()
    app.datearea_y1 = object()
    app.datearea_x2 = object()
    app.datearea_y2 = object()
    app.ratearea_x1 = object()
    app.ratearea_y1 = object()
    app.ratearea_x2 = object()
    app.ratearea_y2 = object()
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "relocate_clickpoint_action",
        lambda app_ref: calls.append(("click", app_ref)),
    )
    monkeypatch.setattr(
        ocr_module,
        "relocate_area_action",
        lambda app_ref, x1, y1, x2, y2, color: calls.append(("area", app_ref, x1, y1, x2, y2, color)),
    )
    monkeypatch.setattr(
        ocr_module,
        "show_area_preview_action",
        lambda app_ref: calls.append(("preview", app_ref)),
    )

    app.relocate_clickpoint()
    app.relocate_allarea()
    app.relocate_datearea()
    app.relocate_ratearea()
    app.show_area_preview()

    assert calls == [
        ("click", app),
        ("area", app, app.allarea_x1, app.allarea_y1, app.allarea_x2, app.allarea_y2, "primary"),
        ("area", app, app.datearea_x1, app.datearea_y1, app.datearea_x2, app.datearea_y2, "success"),
        ("area", app, app.ratearea_x1, app.ratearea_y1, app.ratearea_x2, app.ratearea_y2, "warning"),
        ("preview", app),
    ]
