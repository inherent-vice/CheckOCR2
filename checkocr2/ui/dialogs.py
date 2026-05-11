"""Small messagebox-backed dialogs for the Tk shell."""

from __future__ import annotations

from collections.abc import Callable
from tkinter import messagebox

from checkocr2.build_metadata import format_build_metadata, load_build_metadata

SHORTCUTS_TITLE = "키보드 단축키"
SHORTCUTS_TEXT = """🎹 키보드 단축키:
• F5: OCR 처리 실행/중단
• Escape: 처리 중단
• F1: 단축키 도움말 (이 창)
• Ctrl+S: 모든 설정 저장
• Ctrl+L: 마지막 설정 불러오기
• Ctrl+O: Excel 파일 로드 (그리드)"""

ABOUT_TITLE = "프로그램 정보"


def build_about_text(build_summary: str) -> str:
    return f"""📋 Check Capture OCR - V6
OCR 자동화 애플리케이션 (EasyOCR 기반)

{build_summary}"""


def show_shortcuts_dialog(
    *,
    parent: object,
    showinfo: Callable[..., object] | None = None,
) -> None:
    (showinfo or messagebox.showinfo)(SHORTCUTS_TITLE, SHORTCUTS_TEXT, parent=parent)


def show_about_dialog(
    *,
    parent: object,
    showinfo: Callable[..., object] | None = None,
) -> None:
    build_summary = format_build_metadata(load_build_metadata())
    (showinfo or messagebox.showinfo)(ABOUT_TITLE, build_about_text(build_summary), parent=parent)
