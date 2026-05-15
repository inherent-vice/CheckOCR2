from __future__ import annotations

from types import SimpleNamespace

from checkocr2.runtime_state import RuntimeState
from checkocr2.ui import loading_overlay


def test_update_loading_overlay_creates_and_closes_overlay(monkeypatch):
    overlays = []

    class FakeOverlay:
        def __init__(self, app):
            self.app = app
            self.states = []
            overlays.append(self)

        def set_state(self, state):
            self.states.append(state)

    monkeypatch.setattr(loading_overlay, "OcrLoadingOverlay", FakeOverlay)
    app = SimpleNamespace(tk=object(), ocr_loading_overlay=None)

    loading_overlay.update_loading_overlay_for_state(app, RuntimeState.OCR_LOADING)
    assert app.ocr_loading_overlay is overlays[0]
    assert overlays[0].states == [RuntimeState.OCR_LOADING]

    loading_overlay.update_loading_overlay_for_state(app, RuntimeState.READY)
    assert overlays[0].states == [RuntimeState.OCR_LOADING, RuntimeState.READY]
    assert app.ocr_loading_overlay is None


def test_update_loading_overlay_noops_for_non_tk_test_doubles():
    app = SimpleNamespace(ocr_loading_overlay=None)

    loading_overlay.update_loading_overlay_for_state(app, RuntimeState.OCR_LOADING)

    assert app.ocr_loading_overlay is None
