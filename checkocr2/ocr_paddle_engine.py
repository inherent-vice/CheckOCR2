"""PaddleOCR adapter with an EasyOCR-compatible readtext surface."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .exceptions import OCREngineError
from .startup_trace import paddle_model_cache_state, record_startup_event


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
        record_startup_event(
            "paddle_import_start",
            mode="pipeline",
            diagnostics=paddle_runtime_diagnostics(),
        )
        from paddleocr import PaddleOCR
        record_startup_event("paddle_import_done", mode="pipeline")
    except Exception as exc:
        diagnostics = paddle_runtime_diagnostics()
        record_startup_event(
            "paddle_import_failed",
            mode="pipeline",
            error=str(exc),
            diagnostics=diagnostics,
        )
        raise OCREngineError(
            f"PaddleOCR import failed: {exc}; diagnostics={diagnostics}"
        ) from exc

    params = paddleocr_params(languages, gpu=gpu)
    diagnostics = paddle_runtime_diagnostics(_model_names_from_params(params))
    record_startup_event(
        "paddle_model_cache_check",
        mode="pipeline",
        cache=paddle_model_cache_state(_model_names_from_params(params)),
        diagnostics=diagnostics,
    )
    try:
        reader = PaddleOCR(**params)
    except TypeError:
        fallback_params = dict(params)
        fallback_params.pop("device", None)
        reader = PaddleOCR(**fallback_params)
    except Exception as exc:
        record_startup_event(
            "paddle_reader_failed",
            mode="pipeline",
            error=str(exc),
            diagnostics=diagnostics,
        )
        raise OCREngineError(
            f"PaddleOCR reader initialization failed: {exc}; diagnostics={diagnostics}"
        ) from exc
    record_startup_event("paddle_reader_ready", mode="pipeline")
    return PaddleOcrReaderAdapter(reader)


def create_paddle_text_recognition_reader(
    languages: Sequence[str],
    *,
    gpu: bool = False,
) -> PaddleOcrReaderAdapter:
    try:
        record_startup_event(
            "paddle_import_start",
            mode="recognition",
            diagnostics=paddle_runtime_diagnostics(),
        )
        from paddleocr import TextRecognition
        record_startup_event("paddle_import_done", mode="recognition")
    except Exception as exc:
        diagnostics = paddle_runtime_diagnostics()
        record_startup_event(
            "paddle_import_failed",
            mode="recognition",
            error=str(exc),
            diagnostics=diagnostics,
        )
        raise OCREngineError(
            f"PaddleOCR import failed: {exc}; diagnostics={diagnostics}"
        ) from exc

    params = paddle_recognition_params(languages, gpu=gpu)
    diagnostics = paddle_runtime_diagnostics(_model_names_from_params(params))
    record_startup_event(
        "paddle_model_cache_check",
        mode="recognition",
        cache=paddle_model_cache_state(_model_names_from_params(params)),
        diagnostics=diagnostics,
    )
    try:
        reader = TextRecognition(**params)
    except TypeError:
        fallback_params = dict(params)
        fallback_params.pop("device", None)
        reader = TextRecognition(**fallback_params)
    except Exception as exc:
        record_startup_event(
            "paddle_reader_failed",
            mode="recognition",
            error=str(exc),
            diagnostics=diagnostics,
        )
        raise OCREngineError(
            f"PaddleOCR reader initialization failed: {exc}; diagnostics={diagnostics}"
        ) from exc
    record_startup_event("paddle_reader_ready", mode="recognition")
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
    det_model = os.environ.get("CHECKOCR2_PADDLE_DET_MODEL", "PP-OCRv5_mobile_det")
    rec_model = os.environ.get("CHECKOCR2_PADDLE_REC_MODEL", paddle_recognition_model(languages))
    params.update(
        {
            "lang": paddle_lang(languages),
            "ocr_version": "PP-OCRv5",
            "text_detection_model_name": det_model,
            "text_recognition_model_name": rec_model,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        }
    )
    det_dir = packaged_model_dir(det_model)
    rec_dir = packaged_model_dir(rec_model)
    if det_dir is not None:
        params["text_detection_model_dir"] = str(det_dir)
    if rec_dir is not None:
        params["text_recognition_model_dir"] = str(rec_dir)
    return params


def paddle_recognition_params(languages: Sequence[str], *, gpu: bool = False) -> dict[str, Any]:
    params = paddle_common_params(gpu=gpu)
    model_name = os.environ.get("CHECKOCR2_PADDLE_REC_MODEL", paddle_recognition_model(languages))
    params["model_name"] = model_name
    model_dir = packaged_model_dir(model_name)
    if model_dir is not None:
        params["model_dir"] = str(model_dir)
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


def packaged_model_dir(model_name: str) -> Path | None:
    model_root = os.environ.get("CHECKOCR2_PADDLE_MODEL_ROOT")
    candidates: list[Path] = []
    if model_root:
        candidates.append(Path(model_root))

    runtime_root = getattr(sys, "_MEIPASS", None)
    if runtime_root:
        candidates.append(Path(runtime_root) / "checkocr2" / "paddle_models")
        candidates.append(Path(runtime_root) / "_internal" / "checkocr2" / "paddle_models")

    for root in candidates:
        candidate = root / model_name
        if candidate.is_dir():
            return candidate
    return None


def _model_names_from_params(params: dict[str, Any]) -> list[str]:
    names = []
    for key in ("model_name", "text_detection_model_name", "text_recognition_model_name"):
        value = params.get(key)
        if value:
            names.append(str(value))
    return names


def paddle_runtime_diagnostics(model_names: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "meipass": str(getattr(sys, "_MEIPASS", "")),
        "model_root": os.environ.get("CHECKOCR2_PADDLE_MODEL_ROOT"),
        "pdx_cache": os.environ.get("PADDLE_PDX_CACHE_HOME"),
        "paddle_home": os.environ.get("PADDLE_HOME"),
        "paddleocr_home": os.environ.get("PADDLEOCR_HOME"),
        "protobuf_impl": os.environ.get("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"),
        "cpu_threads": paddle_cpu_threads(),
        "packaged_models": {
            str(model_name): str(model_dir) if (model_dir := packaged_model_dir(str(model_name))) else None
            for model_name in model_names
        },
    }


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
