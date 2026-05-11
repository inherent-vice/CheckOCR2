from __future__ import annotations

from types import SimpleNamespace

import pytest

from checkocr2.ui import overlays as overlays_module


class FakeToplevel:
    def __init__(self, master=None):
        self.master = master
        self.attributes_calls = []
        self.configure_calls = []
        self.bind_calls = []
        self.after_calls = []
        self.focus_set_called = False
        self.destroyed = False
        self.iconphoto_calls = []
        self.iconbitmap_calls = []
        self.iconphoto = lambda *args: self.iconphoto_calls.append(args)
        self.iconbitmap = lambda *args: self.iconbitmap_calls.append(args)
        self.attributes = lambda *args: self.attributes_calls.append(args)
        self.configure = lambda **kwargs: self.configure_calls.append(kwargs)
        self.bind = lambda *args: self.bind_calls.append(args)
        self.after = lambda *args: self.after_calls.append(args)
        self.focus_set = lambda: setattr(self, "focus_set_called", True)
        self.destroy = lambda: setattr(self, "destroyed", True)
        self.winfo_screenwidth = lambda: 1200


class FakeCanvas:
    created = []

    def __init__(self, *args, **kwargs) -> None:
        self.init_args = args
        self.init_kwargs = kwargs
        self.ovals = []
        self.rectangles = []
        self.texts = []
        self.coord_calls = []
        self.bind_calls = []
        self.pack_calls = []
        FakeCanvas.created.append(self)

    def bind(self, *args):
        self.bind_calls.append(args)

    def pack(self, *args, **kwargs):
        self.pack_calls.append((args, kwargs))

    def create_oval(self, *args, **kwargs):
        self.ovals.append((args, kwargs))
        return len(self.ovals)

    def create_rectangle(self, *args, **kwargs):
        self.rectangles.append((args, kwargs))
        return len(self.rectangles)

    def create_text(self, *args, **kwargs):
        self.texts.append((args, kwargs))
        return len(self.texts)

    def coords(self, *args):
        self.coord_calls.append(args)


class FakeTheme:
    def get_color(self, key, default=None):
        return f"color:{key}" if key else default


@pytest.fixture
def fake_tk(monkeypatch):
    FakeCanvas.created.clear()
    monkeypatch.setattr(overlays_module.tk.Toplevel, "__init__", FakeToplevel.__init__)
    monkeypatch.setattr(overlays_module.tk, "Canvas", FakeCanvas)
    monkeypatch.setattr(overlays_module.tk, "BOTH", "both", raising=False)


def test_area_overlay_constructor_wires_fullscreen_canvas_bindings_and_auto_close(fake_tk):
    overlay = overlays_module.AreaVisualizationOverlay(
        SimpleNamespace(_icon_photos=("icon",)),
        {"click_point": (1, 2)},
        FakeTheme(),
        auto_close=True,
    )

    assert overlay.attributes_calls == [("-fullscreen", True), ("-topmost", True), ("-alpha", 0.7)]
    assert overlay.configure_calls == [{"bg": "color:dark"}]
    assert overlay.iconphoto_calls == [(True, "icon")]
    assert FakeCanvas.created[0].init_kwargs == {"bg": "color:dark", "highlightthickness": 0}
    assert FakeCanvas.created[0].pack_calls == [((), {"fill": "both", "expand": True})]
    assert overlay.after_calls[0][0] == 3000
    assert overlay.bind_calls[0][0] == "<KeyPress>"
    assert overlay.focus_set_called is True


def test_drag_and_point_overlay_constructors_bind_mouse_and_escape(fake_tk):
    drag = overlays_module.DragCaptureOverlay(SimpleNamespace(_icon_photos=()), "success", FakeTheme())
    point = overlays_module.PointCaptureOverlay(SimpleNamespace(_icon_photos=()), "danger", FakeTheme())

    drag_canvas, point_canvas = FakeCanvas.created
    assert drag.attributes_calls == [("-fullscreen", True), ("-topmost", True), ("-alpha", 0.3)]
    assert point.attributes_calls == [("-fullscreen", True), ("-topmost", True), ("-alpha", 0.3)]
    assert [call[0] for call in drag_canvas.bind_calls] == ["<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"]
    assert [call[0] for call in point_canvas.bind_calls] == ["<ButtonPress-1>"]
    assert drag.bind_calls[0][0] == "<KeyPress-Escape>"
    assert point.bind_calls[0][0] == "<KeyPress-Escape>"


def test_drag_capture_overlay_records_normalized_coordinates(ocr_module):
    overlay = ocr_module.DragCaptureOverlay.__new__(ocr_module.DragCaptureOverlay)
    overlay.canvas = FakeCanvas()
    overlay.color = "red"
    overlay.destroyed = False
    overlay.destroy = lambda: setattr(overlay, "destroyed", True)

    overlay.on_button_press(SimpleNamespace(x=40, y=50))
    overlay.on_move_press(SimpleNamespace(x=10, y=20))
    overlay.on_button_release(SimpleNamespace(x=10, y=20))

    assert ocr_module.DragCaptureOverlay.__module__ == "checkocr2.ui.overlays"
    assert overlay.rect_id == 1
    assert overlay.canvas.coord_calls == [(1, 40, 50, 10, 20)]
    assert (overlay.x1, overlay.y1, overlay.x2, overlay.y2) == (10, 20, 40, 50)
    assert overlay.destroyed is True


def test_point_capture_overlay_records_click_and_schedules_close(ocr_module):
    overlay = ocr_module.PointCaptureOverlay.__new__(ocr_module.PointCaptureOverlay)
    overlay.canvas = FakeCanvas()
    overlay.color = "blue"
    overlay.after_calls = []
    overlay.destroyed = False
    overlay.destroy = lambda: setattr(overlay, "destroyed", True)

    def after(delay, callback):
        overlay.after_calls.append((delay, callback))
        callback()

    overlay.after = after

    overlay.on_click(SimpleNamespace(x=11, y=22))

    assert ocr_module.PointCaptureOverlay.__module__ == "checkocr2.ui.overlays"
    assert (overlay.click_x, overlay.click_y) == (11, 22)
    assert overlay.canvas.ovals[0] == ((6, 17, 16, 27), {"fill": "blue", "outline": "blue"})
    assert overlay.after_calls[0][0] == 100
    assert overlay.destroyed is True


def test_area_visualization_overlay_draws_click_area_labels_and_escape(ocr_module):
    overlay = ocr_module.AreaVisualizationOverlay.__new__(ocr_module.AreaVisualizationOverlay)
    overlay.theme_manager = FakeTheme()
    overlay.canvas = FakeCanvas()
    overlay.auto_close = True
    overlay.areas_info = {
        "click_point": (30, 40),
        "all_area": (10, 20, 60, 80),
        "date_area": (70, 80, 120, 100),
        "rate_area": (130, 5, 180, 25),
    }
    overlay.winfo_screenwidth = lambda: 1200
    overlay.destroyed = False
    overlay.destroy = lambda: setattr(overlay, "destroyed", True)

    overlay.draw_areas()
    overlay.on_key_press(SimpleNamespace(keysym="Escape"))

    assert ocr_module.AreaVisualizationOverlay.__module__ == "checkocr2.ui.overlays"
    assert len(overlay.canvas.ovals) == 1
    assert len(overlay.canvas.rectangles) == 3
    text_values = [kwargs["text"] for _args, kwargs in overlay.canvas.texts]
    assert "클릭 포인트" in text_values
    assert "전체 영역" in text_values
    assert "날짜 영역" in text_values
    assert "금리 영역" in text_values
    assert "50x60" in text_values
    assert "설정된 영역들이 표시됩니다 (3초 후 자동 종료) | ESC: 종료" in text_values
    assert overlay.destroyed is True
