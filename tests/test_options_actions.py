from __future__ import annotations

from checkocr2.ui import options_actions


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeChild:
    def __init__(self):
        self.pack_configure_calls = 0
        self.pack_forget_calls = 0

    def pack_configure(self):
        self.pack_configure_calls += 1

    def pack_forget(self):
        self.pack_forget_calls += 1


class FakeFrame:
    def __init__(self, children):
        self._children = children

    def winfo_children(self):
        return list(self._children)


class FakeApp:
    def __init__(self, *, enabled=True, has_frame=True):
        self.enable_upscaling = FakeVar(enabled)
        self.children = [FakeChild(), FakeChild()]
        if has_frame:
            self.upscaling_details_frame = FakeFrame(self.children)
        self.saved_advanced = 0

    def save_advanced_ui_to_settings(self):
        self.saved_advanced += 1


def test_toggle_upscaling_details_shows_existing_children_and_saves():
    app = FakeApp(enabled=True)

    options_actions.toggle_upscaling_details(app)

    assert [child.pack_configure_calls for child in app.children] == [1, 1]
    assert [child.pack_forget_calls for child in app.children] == [0, 0]
    assert app.saved_advanced == 1


def test_toggle_upscaling_details_hides_existing_children_and_saves():
    app = FakeApp(enabled=False)

    options_actions.toggle_upscaling_details(app)

    assert [child.pack_configure_calls for child in app.children] == [0, 0]
    assert [child.pack_forget_calls for child in app.children] == [1, 1]
    assert app.saved_advanced == 1


def test_toggle_upscaling_details_without_frame_still_saves():
    app = FakeApp(enabled=False, has_frame=False)

    options_actions.toggle_upscaling_details(app)

    assert app.saved_advanced == 1


def test_legacy_app_upscaling_toggle_delegates(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "toggle_upscaling_details_action",
        lambda app_ref: calls.append(app_ref),
    )

    app.on_upscaling_toggle()

    assert calls == [app]
