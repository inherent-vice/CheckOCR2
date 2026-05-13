"""PaddleOCR adapter with an EasyOCR-compatible readtext surface."""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from typing import Any

from .exceptions import OCREngineError


class PaddleOcrReaderAdapter:
    """Expose PaddleOCR results through the small EasyOCR readtext contract."""

    def __init__(self, reader: Any):
        self.reader = reader

    def readtext(self, image, detail: int = 0, **kwargs: Any):
        try:
            raw_results = self._predict(image)
        except Exception as exc:
            raise OCREngineError(f"PaddleOCR readtext failed: {exc}") from exc
        text_scores = extract_paddle_text_scores(raw_results)
        if detail == 0:
            return [text for text, _score in text_scores]
        return [(None, text, score) for text, score in text_scores]

    def _predict(self, image):
        if hasattr(self.reader, "predict"):
            return self.reader.predict(image)
        if hasattr(self.reader, "ocr"):
            return self.reader.ocr(image)
        raise AttributeError("PaddleOCR reader has no predict or ocr method")


def create_paddleocr_reader(
    languages: Sequence[str],
    *,
    gpu: bool = False,
) -> PaddleOcrReaderAdapter:
    mode = paddle_mode()
    if mode == "pipeline":
        return create_paddleocr_pipeline_reader(languages, gpu=gpu)
    return create_paddle_text_recognition_reader(languages, gpu=gpu)


def create_paddleocr_pipeline_reader(
    languages: Sequence[str],
    *,
    gpu: bool = False,
) -> PaddleOcrReaderAdapter:
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        raise OCREngineError(f"PaddleOCR import failed: {exc}") from exc

    params = paddleocr_params(languages, gpu=gpu)
    try:
        reader = PaddleOCR(**params)
    except TypeError:
        fallback_params = dict(params)
        fallback_params.pop("device", None)
        reader = PaddleOCR(**fallback_params)
    except Exception as exc:
        raise OCREngineError(f"PaddleOCR reader initialization failed: {exc}") from exc
    return PaddleOcrReaderAdapter(reader)


def create_paddle_text_recognition_reader(
    languages: Sequence[str],
    *,
    gpu: bool = False,
) -> PaddleOcrReaderAdapter:
    try:
        from paddleocr import TextRecognition
    except Exception as exc:
        raise OCREngineError(f"PaddleOCR import failed: {exc}") from exc

    params = paddle_recognition_params(languages, gpu=gpu)
    try:
        reader = TextRecognition(**params)
    except TypeError:
        fallback_params = dict(params)
        fallback_params.pop("device", None)
        reader = TextRecognition(**fallback_params)
    except Exception as exc:
        raise OCREngineError(f"PaddleOCR reader initialization failed: {exc}") from exc
    return PaddleOcrReaderAdapter(reader)


def paddle_mode() -> str:
    mode = os.environ.get("CHECKOCR2_PADDLE_MODE", "recognition").strip().lower()
    if mode in {"recognition", "rec", "text_recognition"}:
        return "recognition"
    if mode in {"pipeline", "ocr", "detection"}:
        return "pipeline"
    raise OCREngineError(f"unsupported PaddleOCR mode: {mode}")


def paddleocr_params(languages: Sequence[str], *, gpu: bool = False) -> dict[str, Any]:
    params = paddle_common_params(gpu=gpu)
    params.update(
        {
            "lang": paddle_lang(languages),
            "ocr_version": "PP-OCRv5",
            "text_detection_model_name": os.environ.get(
                "CHECKOCR2_PADDLE_DET_MODEL",
                "PP-OCRv5_mobile_det",
            ),
            "text_recognition_model_name": os.environ.get(
                "CHECKOCR2_PADDLE_REC_MODEL",
                paddle_recognition_model(languages),
            ),
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        }
    )
    return params


def paddle_recognition_params(languages: Sequence[str], *, gpu: bool = False) -> dict[str, Any]:
    params = paddle_common_params(gpu=gpu)
    params["model_name"] = os.environ.get(
        "CHECKOCR2_PADDLE_REC_MODEL",
        paddle_recognition_model(languages),
    )
    return params


def paddle_common_params(*, gpu: bool = False) -> dict[str, Any]:
    device_type = "gpu" if gpu else "cpu"
    params: dict[str, Any] = {
        "device": "gpu:0" if gpu else "cpu",
        "engine": "paddle_static",
        "engine_config": {
            "device_type": device_type,
            "run_mode": "paddle",
            "cpu_threads": paddle_cpu_threads(),
        },
        "enable_mkldnn": False,
    }
    if gpu:
        params["engine_config"].pop("cpu_threads", None)
    return params


def paddle_lang(languages: Sequence[str]) -> str:
    normalized = {str(language).strip().lower() for language in languages}
    if "korean" in normalized or "ko" in normalized or "kr" in normalized:
        return "korean"
    return "en"


def paddle_recognition_model(languages: Sequence[str]) -> str:
    if paddle_lang(languages) == "korean":
        return "korean_PP-OCRv5_mobile_rec"
    return "en_PP-OCRv5_mobile_rec"


def paddle_cpu_threads() -> int:
    try:
        configured = int(os.environ.get("CHECKOCR2_PADDLE_CPU_THREADS", "4"))
    except ValueError:
        configured = 4
    cpu_count = os.cpu_count() or configured
    return max(1, min(configured, cpu_count))


def extract_paddle_text_scores(results: Any) -> list[tuple[str, float | None]]:
    extracted: list[tuple[str, float | None]] = []
    for item in flatten_result_items(results):
        texts = value_from_item(item, "rec_texts")
        if texts is None:
            text = value_from_item(item, "rec_text")
            texts = [text] if text is not None else None
        if texts is None:
            continue
        scores = value_from_item(item, "rec_scores")
        if scores is None:
            score = value_from_item(item, "rec_score")
            scores = [score] if score is not None else []
        score_values = listify(scores)
        for index, text in enumerate(listify(texts)):
            if text is None:
                continue
            score = score_values[index] if index < len(score_values) else None
            extracted.append((str(text).strip(), normalize_score(score)))
    return [(text, score) for text, score in extracted if text]


def flatten_result_items(results: Any) -> Iterable[Any]:
    if results is None:
        return []
    if isinstance(results, dict):
        return [results]
    if isinstance(results, str | bytes):
        return []
    try:
        iterator = iter(results)
    except TypeError:
        return [results]
    items: list[Any] = []
    for item in iterator:
        if isinstance(item, list | tuple) and not value_from_item(item, "rec_texts"):
            items.extend(flatten_result_items(item))
        else:
            items.append(item)
    return items


def value_from_item(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def normalize_score(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
