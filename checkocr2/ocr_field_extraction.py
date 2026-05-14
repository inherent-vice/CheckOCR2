"""Single-field OCR extraction orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

import numpy as np
from PIL import Image

from .exceptions import OCREngineError
from .image_processing import cleanup_temp_ocr_image
from .ocr_engine import (
    confidence_is_accepted,
    extract_text_with_confidence,
    normalize_confidence_threshold,
    read_ocr_text,
)
from .ocr_field_analysis import analyze_date_field, analyze_rate_field


class LoggerLike(Protocol):
    def exception(self, message: str) -> None: ...


@dataclass(frozen=True)
class OcrFieldExtractionResult:
    value: str
    timing_ms: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None


def select_field_text_from_ocr_results(
    results: Any,
    field_key: str,
) -> str:
    texts = ocr_result_texts(results)
    field = field_key.lower()
    if field == "date":
        for text in texts:
            analysis = analyze_date_field(text, "date")
            if analysis.value:
                return analysis.value
        return ""
    if field == "rate":
        for text in texts:
            if not any(separator in text for separator in (".", ",", "%")):
                continue
            analysis = analyze_rate_field(text, "rate")
            if analysis.value:
                return analysis.value
        for text in texts:
            analysis = analyze_rate_field(text, "rate")
            if analysis.value:
                return analysis.value
        return ""
    return ""


def ocr_result_texts(results: Any) -> list[str]:
    texts: list[str] = []
    if results is None:
        return texts
    try:
        iterator = iter(results)
    except TypeError:
        return [str(results).strip()]
    for item in iterator:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, list | tuple) and len(item) >= 2:
            text = str(item[1]).strip()
        else:
            text = str(item).strip()
        if text:
            texts.append(text)
    return texts


def elapsed_ms(started_at: float, *, timer: Callable[[], float] = perf_counter) -> float:
    return round((timer() - started_at) * 1000, 3)


def extract_ocr_field_text(
    image_source: str | Image.Image | None,
    *,
    reader: Any,
    field_key: str,
    field_name: str,
    save_details: bool,
    get_advanced: Callable[[str, Any], Any],
    get_detail_level: Callable[[], int],
    get_min_confidence: Callable[[str], Any],
    is_stopped: Callable[[], bool],
    emit_log: Callable[[str, str], None],
    analyze_text: Callable[[str, str], str],
    apply_upscaling: Callable[[Image.Image, bool, float, str], Image.Image],
    logger: LoggerLike,
    record_timing: Callable[[str, float], None] | None = None,
    record_confidence: Callable[[float], None] | None = None,
    timer: Callable[[], float] = perf_counter,
    image_open: Callable[[str], Image.Image] = Image.open,
    array_factory: Callable[[Image.Image], Any] = np.array,
    read_ocr_text_func: Callable[..., Any] = read_ocr_text,
    extract_text_with_confidence_func: Callable[..., tuple[str, float | None]] = extract_text_with_confidence,
    confidence_is_accepted_func: Callable[[float | None, Any], bool] = confidence_is_accepted,
    normalize_confidence_threshold_func: Callable[[Any], float] = normalize_confidence_threshold,
    cleanup_temp_ocr_image_func: Callable[..., Any] = cleanup_temp_ocr_image,
) -> OcrFieldExtractionResult:
    if is_stopped():
        return OcrFieldExtractionResult("")

    timing_ms: dict[str, float] = {}
    confidence_value: float | None = None
    parsed_text = ""
    extract_started = timer()

    def set_timing(name: str, value: float) -> None:
        timing_ms[name] = value
        if record_timing is not None:
            record_timing(name, value)

    try:
        image_load_started = timer()
        original_img = image_open(image_source) if isinstance(image_source, str) else image_source
        set_timing(f"{field_key}_image_load_ms", elapsed_ms(image_load_started, timer=timer))
        if original_img is None:
            emit_log(f"{field_name} 이미지 소스 로드 실패: {image_source}", "WARNING")
            return OcrFieldExtractionResult("", timing_ms)

        if is_stopped():
            return OcrFieldExtractionResult("", timing_ms)

        upscaling_enabled = get_advanced("upscaling_enabled", True)
        upscaling_factor = get_advanced("upscaling_factor", 2.0)
        upscaling_method = get_advanced("upscaling_method", "LANCZOS")

        preprocess_started = timer()
        processed_img = apply_upscaling(
            original_img,
            upscaling_enabled,
            upscaling_factor,
            upscaling_method,
        )
        img_array = array_factory(processed_img)
        set_timing(f"{field_key}_preprocess_ms", elapsed_ms(preprocess_started, timer=timer))

        ocr_started = timer()
        detail_level = get_detail_level()
        ocr_results = read_ocr_text_func(reader, img_array, detail=detail_level)
        set_timing(f"{field_key}_ocr_ms", elapsed_ms(ocr_started, timer=timer))
        all_text, confidence = extract_text_with_confidence_func(ocr_results, detail_level)
        if confidence is not None:
            confidence_value = round(confidence, 4)
            if record_confidence is not None:
                record_confidence(confidence_value)

        min_confidence = get_min_confidence(field_key)
        if detail_level == 1 and not confidence_is_accepted_func(
            confidence,
            min_confidence,
        ):
            threshold = normalize_confidence_threshold_func(min_confidence)
            emit_log(
                f"[{field_name}] OCR confidence below threshold: {confidence} < {threshold}",
                "WARNING",
            )
            return OcrFieldExtractionResult("", timing_ms, confidence_value)

        scale_info = (
            f" (업스케일링: {upscaling_factor}x {upscaling_method})"
            if upscaling_enabled and upscaling_factor > 1.0
            else ""
        )
        emit_log(f"[{field_name}] OCR 결과{scale_info}: '{all_text}'", "INFO")

        parse_started = timer()
        parsed_text = analyze_text(all_text, field_name)
        set_timing(f"{field_key}_parse_ms", elapsed_ms(parse_started, timer=timer))
        return OcrFieldExtractionResult(parsed_text, timing_ms, confidence_value)
    except (OSError, RuntimeError, TypeError, ValueError, OCREngineError) as exc:
        emit_log(f"{field_name} 추출 중 오류: {exc}", "ERROR")
        logger.exception(f"{field_name} 추출 중 예외 발생")
        return OcrFieldExtractionResult("", timing_ms, confidence_value)
    finally:
        set_timing(f"{field_key}_total_ms", elapsed_ms(extract_started, timer=timer))
        cleanup = cleanup_temp_ocr_image_func(
            image_source,
            save_details=save_details,
            field_name=field_name,
        )
        if cleanup.log_event is not None:
            message, level = cleanup.log_event
            emit_log(message, level)
