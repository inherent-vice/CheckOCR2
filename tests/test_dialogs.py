from __future__ import annotations

from checkocr2.ui.dialogs import build_about_text, show_about_dialog, show_shortcuts_dialog

EXPECTED_SHORTCUTS_TITLE = "키보드 단축키"
EXPECTED_SHORTCUTS_TEXT = """🎹 키보드 단축키:
• F5: OCR 처리 실행/중단
• Escape: 처리 중단
• F1: 단축키 도움말 (이 창)
• Ctrl+S: 모든 설정 저장
• Ctrl+L: 마지막 설정 불러오기
• Ctrl+O: Excel 파일 로드 (그리드)"""
EXPECTED_ABOUT_TITLE = "프로그램 정보"
EXPECTED_ABOUT_TEXT = """📋 Check Capture OCR - V6
OCR 자동화 애플리케이션 (EasyOCR 기반)

Build: test"""


def test_show_shortcuts_dialog_uses_existing_title_and_text():
    calls = []

    show_shortcuts_dialog(parent="app", showinfo=lambda *args, **kwargs: calls.append((args, kwargs)))

    assert calls == [((EXPECTED_SHORTCUTS_TITLE, EXPECTED_SHORTCUTS_TEXT), {"parent": "app"})]


def test_show_about_dialog_includes_build_summary(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "checkocr2.ui.dialogs.load_build_metadata",
        lambda: {"app_version": "V6.1", "python_version": "3.12"},
    )
    monkeypatch.setattr("checkocr2.ui.dialogs.format_build_metadata", lambda _metadata: "Build: test")

    show_about_dialog(parent="app", showinfo=lambda *args, **kwargs: calls.append((args, kwargs)))

    assert build_about_text("Build: test") == EXPECTED_ABOUT_TEXT
    assert calls == [((EXPECTED_ABOUT_TITLE, EXPECTED_ABOUT_TEXT), {"parent": "app"})]


def test_app_dialog_wrappers_delegate_to_dialog_module(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "show_shortcuts_dialog",
        lambda *, parent: calls.append(("shortcuts", parent)),
    )
    monkeypatch.setattr(
        ocr_module,
        "show_about_dialog",
        lambda *, parent: calls.append(("about", parent)),
    )

    app.show_shortcuts()
    app.show_about()

    assert calls == [("shortcuts", app), ("about", app)]
