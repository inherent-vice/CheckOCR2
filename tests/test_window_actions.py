from __future__ import annotations

from checkocr2.ui import window_actions


class FakeWindow:
    def __init__(
        self,
        *,
        screen_width=1920,
        screen_height=1080,
        window_width=1200,
        window_height=850,
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.window_width = window_width
        self.window_height = window_height
        self.update_count = 0
        self.geometry_calls = []

    def update_idletasks(self):
        self.update_count += 1

    def winfo_screenwidth(self):
        return self.screen_width

    def winfo_screenheight(self):
        return self.screen_height

    def winfo_width(self):
        return self.window_width

    def winfo_height(self):
        return self.window_height

    def geometry(self, value):
        self.geometry_calls.append(value)


def test_build_centered_geometry_uses_legacy_integer_centering():
    assert (
        window_actions.build_centered_geometry(
            screen_width=1920,
            screen_height=1080,
            window_width=1200,
            window_height=850,
        )
        == "1200x850+360+115"
    )


def test_build_centered_geometry_allows_negative_offsets_for_large_windows():
    assert (
        window_actions.build_centered_geometry(
            screen_width=100,
            screen_height=80,
            window_width=120,
            window_height=90,
        )
        == "120x90+-10+-5"
    )


def test_center_window_updates_layout_then_applies_geometry():
    window = FakeWindow()

    window_actions.center_window(window)

    assert window.update_count == 1
    assert window.geometry_calls == ["1200x850+360+115"]


def test_legacy_center_window_delegates(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "center_window_action",
        lambda app_ref: calls.append(app_ref),
    )

    app.center_window()

    assert calls == [app]
