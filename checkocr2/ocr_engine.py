"""OCR engine adapter seam."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from typing import Any, Protocol

from .exceptions import OCREngineError


class EasyOcrReaderLike(Protocol):
    def readtext(self, image, detail: int = 0, **kwargs: Any): ...


def create_easyocr_reader(languages: Sequence[str], *, gpu: bool = False) -> EasyOcrReaderLike:
    try:
        import easyocr
    except ImportError as exc:
        raise OCREngineError(f"EasyOCR import failed: {exc}") from exc

    try:
        return easyocr.Reader(list(languages), gpu=gpu)
    except Exception as exc:
        raise OCREngineError(f"EasyOCR reader initialization failed: {exc}") from exc


def read_ocr_text(reader: EasyOcrReaderLike, image, *, detail: int = 0, allowlist: str | None = None):
    kwargs: dict[str, Any] = {"detail": detail}
    if allowlist is not None:
        kwargs["allowlist"] = allowlist
    try:
        return reader.readtext(image, **kwargs)
    except Exception as exc:
        raise OCREngineError(f"EasyOCR readtext failed: {exc}") from exc


def extract_text_with_confidence(results: Sequence[Any], detail: int) -> tuple[str, float | None]:
    if detail == 0:
        return " ".join(str(item) for item in results).strip(), None

    texts: list[str] = []
    confidences: list[float] = []
    for item in results:
        if isinstance(item, list | tuple) and len(item) >= 3:
            texts.append(str(item[1]))
            try:
                confidences.append(float(item[2]))
            except (TypeError, ValueError):
                pass
    confidence = statistics.fmean(confidences) if confidences else None
    return " ".join(texts).strip(), confidence


def normalize_confidence_threshold(value: Any) -> float:
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        return 0.0
    if threshold <= 0:
        return 0.0
    if threshold > 1:
        threshold /= 100.0
    return min(threshold, 1.0)


def confidence_is_accepted(confidence: float | None, threshold: Any) -> bool:
    normalized_threshold = normalize_confidence_threshold(threshold)
    if normalized_threshold <= 0:
        return True
    return confidence is not None and confidence >= normalized_threshold
