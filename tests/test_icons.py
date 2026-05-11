from __future__ import annotations

from checkocr2.ui.icons import apply_application_icon, first_existing_path


class FakeWindow:
    def __init__(self) -> None:
        self.iconbitmap_calls = []
        self.iconphoto_calls = []

    def iconbitmap(self, path):
        self.iconbitmap_calls.append(path)

    def iconphoto(self, *args):
        self.iconphoto_calls.append(args)


class FakeImage:
    def __init__(self) -> None:
        self.resize_calls = []

    def resize(self, size, resample):
        self.resize_calls.append((size, resample))
        return f"resized-{size[0]}"


def test_first_existing_path_returns_first_available_candidate():
    existing = {"fallback.ico"}

    assert (
        first_existing_path(
            ["missing.ico", "fallback.ico"],
            exists=existing.__contains__,
        )
        == "fallback.ico"
    )


def test_apply_application_icon_uses_preferred_ico_and_png():
    window = FakeWindow()
    image = FakeImage()
    messages = []
    existing = {"eye_ocr_02_scanline.ico", "eye_ocr_02_scanline.png"}

    apply_application_icon(
        window,
        exists=existing.__contains__,
        print_func=messages.append,
        image_open=lambda path: image,
        photo_factory=lambda resized: f"photo-{resized}",
    )

    assert window.iconbitmap_calls == ["eye_ocr_02_scanline.ico"]
    assert [call[0] for call in image.resize_calls] == [(16, 16), (32, 32), (48, 48)]
    assert window._icon_photos == [
        "photo-resized-16",
        "photo-resized-32",
        "photo-resized-48",
    ]
    assert window.iconphoto_calls == [
        (True, "photo-resized-16", "photo-resized-32", "photo-resized-48")
    ]
    assert "ICO 아이콘 설정 완료: eye_ocr_02_scanline.ico" in messages
    assert "PNG 아이콘 설정 완료: eye_ocr_02_scanline.png (3개 크기)" in messages


def test_apply_application_icon_reports_missing_icons_without_calls():
    window = FakeWindow()
    messages = []

    apply_application_icon(
        window,
        exists=lambda _path: False,
        print_func=messages.append,
    )

    assert window.iconbitmap_calls == []
    assert window.iconphoto_calls == []
    assert messages == ["아이콘 파일을 찾을 수 없습니다."]


def test_legacy_app_icon_method_delegates_to_package_helper(ocr_module, monkeypatch):
    calls = []
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)

    monkeypatch.setattr(
        ocr_module,
        "apply_application_icon",
        lambda window: calls.append(window),
    )

    app._setup_application_icon()

    assert calls == [app]
