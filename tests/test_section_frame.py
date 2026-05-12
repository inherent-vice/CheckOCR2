from __future__ import annotations

import tkinter as tk
from typing import ClassVar, cast

from checkocr2.ui import section_frame


class FakeWidget:
    created: ClassVar[list[object]] = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.__class__.created.append(self)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)


class FakeFrame(FakeWidget):
    created: ClassVar[list[object]] = []


class FakeLabel(FakeWidget):
    created: ClassVar[list[object]] = []


class FakeThemeManager:
    def __init__(self):
        self.registered = []

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))


class FakeApp:
    def __init__(self):
        self.theme_manager = FakeThemeManager()


def _patch_tk(monkeypatch):
    FakeFrame.created = []
    FakeLabel.created = []
    monkeypatch.setattr(section_frame.tk, "Frame", FakeFrame, raising=False)
    monkeypatch.setattr(section_frame.tk, "Label", FakeLabel, raising=False)


def test_create_section_frame_styled_preserves_default_section_layout(monkeypatch):
    _patch_tk(monkeypatch)
    app = FakeApp()
    parent = cast(tk.Misc, object())

    content_frame = section_frame.create_section_frame_styled(
        app,
        parent,
        "파일 설정",
    )

    outer_frame, inner_frame = FakeFrame.created
    title_label = FakeLabel.created[0]

    assert content_frame is inner_frame
    assert outer_frame.args == (parent,)
    assert outer_frame.pack_calls == [{"fill": "x", "padx": 3, "pady": 3}]
    assert title_label.args == (outer_frame,)
    assert title_label.kwargs == {
        "text": "파일 설정",
        "anchor": "w",
        "font": ("Segoe UI", 10, "bold"),
    }
    assert title_label.pack_calls == [{"fill": "x", "pady": (0, 5)}]
    assert inner_frame.args == (outer_frame,)
    assert inner_frame.pack_calls == [{"fill": "both", "expand": True}]
    assert app.theme_manager.registered == [
        (
            outer_frame,
            {"bg": "surface", "relief": "groove", "bd": 1, "padx": 3, "pady": 3},
        ),
        (title_label, {"bg": "surface", "fg": "primary"}),
        (
            inner_frame,
            {"bg": "white", "padx": 3, "pady": 3, "relief": "solid", "bd": 1},
        ),
    ]


def test_create_section_frame_styled_can_fill_parent(monkeypatch):
    _patch_tk(monkeypatch)
    app = FakeApp()

    section_frame.create_section_frame_styled(
        app,
        cast(tk.Misc, object()),
        "Excel 데이터 그리드",
        fill_parent=True,
    )

    outer_frame = FakeFrame.created[0]
    assert outer_frame.pack_calls == [
        {"fill": "both", "expand": True, "padx": 3, "pady": 3}
    ]


def test_legacy_section_frame_method_delegates(ocr_module, monkeypatch):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    def fake_create_section_frame(app_ref, parent, title, *, fill_parent=False):
        calls.append((app_ref, parent, title, fill_parent))
        return "content"

    monkeypatch.setattr(
        ocr_module, "create_section_frame_action", fake_create_section_frame
    )

    result = app._create_section_frame_styled("parent", "title", fill_parent=True)

    assert result == "content"
    assert calls == [(app, "parent", "title", True)]


def test_legacy_section_frame_method_preserves_positional_fill_parent(
    ocr_module,
    monkeypatch,
):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    def fake_create_section_frame(app_ref, parent, title, *, fill_parent=False):
        calls.append((app_ref, parent, title, fill_parent))
        return "content"

    monkeypatch.setattr(
        ocr_module, "create_section_frame_action", fake_create_section_frame
    )

    result = app._create_section_frame_styled("parent", "title", True)

    assert result == "content"
    assert calls == [(app, "parent", "title", True)]
