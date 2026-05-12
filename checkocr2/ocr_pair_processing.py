"""Date/rate OCR pair processing helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .exceptions import OCREngineError


class LoggerLike(Protocol):
    def exception(self, message: str) -> None: ...


def process_ocr_image_pair(
    date_img_src,
    rate_img_src,
    *,
    save_details: bool,
    extract_text: Callable[[object, Callable[..., str], str, bool], str],
    analyze_date: Callable[..., str],
    analyze_rate: Callable[..., str],
    emit_log: Callable[[str, str], None],
    logger: LoggerLike,
) -> tuple[str, str]:
    date_result, rate_result = "", ""
    try:
        if date_img_src:
            date_result = extract_text(date_img_src, analyze_date, "날짜", save_details)
        if rate_img_src:
            rate_result = extract_text(rate_img_src, analyze_rate, "금리", save_details)
    except (OSError, RuntimeError, TypeError, ValueError, OCREngineError) as exc:
        emit_log(f"단일 OCR 처리 중 오류: {exc}", "ERROR")
        logger.exception("단일 OCR 처리 중 예외 발생")
    return date_result, rate_result
