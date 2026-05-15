"""OCR engine adapter seam."""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from time import perf_counter
from typing import Any, Protocol

from .exceptions import OCREngineError

OCR_ENGINE_EASYOCR = "easyocr"
OCR_ENGINE_PADDLE = "paddle"
SUPPORTED_OCR_ENGINES = (OCR_ENGINE_EASYOCR, OCR_ENGINE_PADDLE)


class EasyOcrReaderLike(Protocol):
    def readtext(self, image, detail: int = 0, **kwargs: Any): ...


class BlankFallbackOcrReader:
    """Use a secondary reader only when the primary reader returns no text."""

    def __init__(
        self,
        primary: EasyOcrReaderLike,
        fallback: EasyOcrReaderLike | None = None,
        *,
        fallback_factory: Any = None,
        primary_engine: str = OCR_ENGINE_PADDLE,
        fallback_engine: str = OCR_ENGINE_EASYOCR,
    ):
        if fallback is None and fallback_factory is None:
            raise ValueError("fallback or fallback_factory is required")
        self.primary = primary
        self.fallback = fallback
        self._fallback_factory = fallback_factory
        self.primary_engine = primary_engine
        self.fallback_engine = fallback_engine
        self.fallback_count = 0
        self.fallback_load_count = 1 if fallback is not None else 0
        self.fallback_init_ms: float | None = None

    @property
    def fallback_loaded(self) -> bool:
        return self.fallback is not None

    def readtext(self, image, detail: int = 0, **kwargs: Any):
        primary_results = self.primary.readtext(image, detail=detail, **kwargs)
        if ocr_results_have_text(primary_results, detail):
            return primary_results
        self.fallback_count += 1
        fallback = self._fallback_reader()
        return fallback.readtext(image, detail=detail, **kwargs)

    def _fallback_reader(self) -> EasyOcrReaderLike:
        if self.fallback is not None:
            return self.fallback
        started_at = perf_counter()
        self.fallback = self._fallback_factory()
        self.fallback_load_count += 1
        self.fallback_init_ms = round((perf_counter() - started_at) * 1000, 3)
        return self.fallback


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


def ocr_results_have_text(results: Sequence[Any], detail: int) -> bool:
    text, _confidence = extract_text_with_confidence(results, detail)
    return bool(text.strip())


def reader_fallback_count(reader: Any) -> int:
    try:
        return max(0, int(getattr(reader, "fallback_count", 0) or 0))
    except (TypeError, ValueError):
        return 0


def reader_engine_metadata(reader: Any) -> dict[str, Any]:
    if reader is None:
        return {
            "actual_ocr_engine": None,
            "ocr_fallback_enabled": False,
            "ocr_fallback_engine": None,
            "ocr_fallback_count": 0,
            "ocr_fallback_loaded": False,
            "ocr_fallback_load_count": 0,
            "ocr_fallback_init_ms": None,
        }
    if isinstance(reader, BlankFallbackOcrReader):
        return {
            "actual_ocr_engine": reader.primary_engine,
            "ocr_fallback_enabled": True,
            "ocr_fallback_engine": reader.fallback_engine,
            "ocr_fallback_count": reader_fallback_count(reader),
            "ocr_fallback_loaded": reader.fallback_loaded,
            "ocr_fallback_load_count": reader.fallback_load_count,
            "ocr_fallback_init_ms": reader.fallback_init_ms,
        }

    module_name = type(reader).__module__.casefold()
    if "ocr_paddle_engine" in module_name:
        actual_engine = OCR_ENGINE_PADDLE
    elif module_name.startswith("easyocr"):
        actual_engine = OCR_ENGINE_EASYOCR
    else:
        actual_engine = None
    return {
        "actual_ocr_engine": actual_engine,
        "ocr_fallback_enabled": False,
        "ocr_fallback_engine": None,
        "ocr_fallback_count": reader_fallback_count(reader),
        "ocr_fallback_loaded": False,
        "ocr_fallback_load_count": 0,
        "ocr_fallback_init_ms": None,
    }


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
