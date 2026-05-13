"""OCR engine adapter seam."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from typing import Any, Protocol

from .exceptions import OCREngineError

OCR_ENGINE_EASYOCR = "easyocr"
OCR_ENGINE_PADDLE = "paddle"
SUPPORTED_OCR_ENGINES = (OCR_ENGINE_EASYOCR, OCR_ENGINE_PADDLE)


class EasyOcrReaderLike(Protocol):
    def readtext(self, image, detail: int = 0, **kwargs: Any): ...


def normalize_ocr_engine(value: Any) -> str:
    normalized = str(value or OCR_ENGINE_EASYOCR).strip().lower()
    if normalized in {"", "easy", "easyocr"}:
        return OCR_ENGINE_EASYOCR
    if normalized in {"paddle", "paddleocr"}:
        return OCR_ENGINE_PADDLE
    raise OCREngineError(f"unsupported OCR engine: {value}")


def default_ocr_languages(engine: Any) -> list[str]:
    engine_name = normalize_ocr_engine(engine)
    if engine_name == OCR_ENGINE_PADDLE:
        return ["ko", "en"]
    return ["en"]


def create_ocr_reader(
    engine: Any,
    languages: Sequence[str],
    *,
    gpu: bool = False,
    easyocr_factory=None,
    paddle_factory=None,
) -> EasyOcrReaderLike:
    engine_name = normalize_ocr_engine(engine)
    if easyocr_factory is None:
        easyocr_factory = create_easyocr_reader
    if engine_name == OCR_ENGINE_EASYOCR:
        return easyocr_factory(languages, gpu=gpu)
    if paddle_factory is None:
        from .ocr_paddle_engine import create_paddleocr_reader

        paddle_factory = create_paddleocr_reader
    return paddle_factory(languages, gpu=gpu)


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
    except OCREngineError:
        raise
    except Exception as exc:
        raise OCREngineError(f"OCR readtext failed: {exc}") from exc


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
