"""OCR start validation messages for the Tk shell."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

WARNING = "warning"
ERROR = "error"


@dataclass(frozen=True)
class OcrStartValidation:
    is_valid: bool
    severity: str | None = None
    title: str = ""
    message: str = ""


def validate_ocr_start(
    *,
    rows: Sequence[Any],
    output_dir_exists: Callable[[], bool],
    ocr_initializing: bool,
    ocr_ready: bool,
) -> OcrStartValidation:
    if not rows:
        return OcrStartValidation(
            False,
            WARNING,
            "경고",
            "처리할 데이터가 없습니다. Excel 파일을 로드하거나 데이터를 추가하세요.",
        )
    if not output_dir_exists():
        return OcrStartValidation(False, WARNING, "경고", "유효한 Output 폴더를 지정하세요.")
    if ocr_initializing:
        return OcrStartValidation(
            False,
            WARNING,
            "OCR 준비 중",
            "OCR 엔진을 초기화하고 있습니다. 잠시 후 다시 시작하세요.",
        )
    if not ocr_ready:
        return OcrStartValidation(
            False,
            ERROR,
            "오류",
            "OCR 엔진이 초기화되지 않았습니다. 프로그램을 재시작하거나 설정을 확인하세요.",
        )
    return OcrStartValidation(True)
