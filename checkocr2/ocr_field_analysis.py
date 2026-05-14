"""OCR field analysis helpers that preserve legacy log text."""

from __future__ import annotations

from dataclasses import dataclass

from .ocr_runtime_options import DEFAULT_RATE_DECIMAL_PLACES
from .ocr_text import (
    clean_date_text,
    clean_rate_text,
    is_valid_date_format,
    is_valid_rate_format,
)


@dataclass(frozen=True, slots=True)
class OcrFieldAnalysis:
    value: str
    log_events: tuple[tuple[str, str], ...]


def analyze_date_field(raw_text: str | None, field_name: str = "날짜") -> OcrFieldAnalysis:
    if not raw_text or not raw_text.strip():
        return OcrFieldAnalysis(
            "",
            ((f"[{field_name}] 텍스트가 비어있습니다.", "DEBUG"),),
        )

    cleaned_text = clean_date_text(raw_text)
    log_events = [(f"[{field_name}] 원본 텍스트: '{raw_text}'", "DEBUG")]
    if is_valid_date_format(cleaned_text):
        log_events.append((f"[{field_name}] 유효한 날짜: '{cleaned_text}'", "DEBUG"))
        return OcrFieldAnalysis(cleaned_text, tuple(log_events))

    log_events.append(
        (
            f"[{field_name}] 유효하지 않은 날짜 형식: '{cleaned_text}' (원본: '{raw_text}')",
            "DEBUG",
        )
    )
    return OcrFieldAnalysis("", tuple(log_events))


def analyze_rate_field(
    raw_text: str | None,
    field_name: str = "금리",
    *,
    precision: int = DEFAULT_RATE_DECIMAL_PLACES,
) -> OcrFieldAnalysis:
    if not raw_text or not raw_text.strip():
        return OcrFieldAnalysis(
            "",
            ((f"[{field_name}] 텍스트가 비어있습니다.", "DEBUG"),),
        )

    cleaned_text = clean_rate_text(raw_text, precision=precision)
    log_events = [(f"[{field_name}] 원본 텍스트: '{raw_text}'", "DEBUG")]
    if is_valid_rate_format(cleaned_text):
        log_events.append((f"[{field_name}] 유효한 금리: '{cleaned_text}'", "DEBUG"))
        return OcrFieldAnalysis(cleaned_text, tuple(log_events))

    log_events.append(
        (
            f"[{field_name}] 유효하지 않은 금리 형식: '{cleaned_text}' (원본: '{raw_text}')",
            "DEBUG",
        )
    )
    return OcrFieldAnalysis("", tuple(log_events))
