from __future__ import annotations

import sys
import types

import pytest

from checkocr2.exceptions import OCREngineError
from checkocr2.ocr_paddle_engine import (
    PaddleOcrReaderAdapter,
    create_paddleocr_reader,
    extract_paddle_text_scores,
    paddle_recognition_model,
)


def test_extract_paddle_text_scores_reads_rec_texts_and_scores_from_dict():
    payload = [{"rec_texts": ["2026/05/13", "2.750"], "rec_scores": [0.9, 0.8]}]

    assert extract_paddle_text_scores(payload) == [
        ("2026/05/13", pytest.approx(0.9)),
        ("2.750", pytest.approx(0.8)),
    ]


def test_extract_paddle_text_scores_reads_object_attributes():
    payload = types.SimpleNamespace(rec_texts=["2026/05/13"], rec_scores=[0.95])

    assert extract_paddle_text_scores([payload]) == [("2026/05/13", pytest.approx(0.95))]


def test_paddle_adapter_returns_easyocr_compatible_detail_modes():
    class FakePaddle:
        def __init__(self):
            self.calls = []

        def predict(self, image):
            self.calls.append(image)
            return [{"rec_texts": ["2026/05/13"], "rec_scores": [0.91]}]

    paddle = FakePaddle()
    adapter = PaddleOcrReaderAdapter(paddle)

    assert adapter.readtext("image", detail=0) == ["2026/05/13"]
    assert adapter.readtext("image", detail=1) == [(None, "2026/05/13", pytest.approx(0.91))]
    assert paddle.calls == ["image", "image"]


def test_paddle_adapter_falls_back_to_ocr_method():
    class FakePaddle:
        def ocr(self, image):
            return [{"rec_texts": ["2.750"], "rec_scores": [0.88]}]

    assert PaddleOcrReaderAdapter(FakePaddle()).readtext("image", detail=0) == ["2.750"]


def test_create_paddleocr_reader_wraps_text_recognition_module(monkeypatch):
    created = {}

    class FakeTextRecognition:
        def __init__(self, **kwargs):
            created.update(kwargs)

        def predict(self, image):
            return [{"rec_text": "ok", "rec_score": 1.0}]

    monkeypatch.setitem(
        sys.modules,
        "paddleocr",
        types.SimpleNamespace(TextRecognition=FakeTextRecognition),
    )

    reader = create_paddleocr_reader(["ko", "en"], gpu=False)

    assert isinstance(reader, PaddleOcrReaderAdapter)
    assert created["device"] == "cpu"
    assert created["engine"] == "paddle_static"
    assert created["engine_config"]["device_type"] == "cpu"
    assert created["engine_config"]["run_mode"] == "paddle"
    assert created["model_name"] == "korean_PP-OCRv5_mobile_rec"
    assert created["enable_mkldnn"] is False
    assert reader.readtext("image") == ["ok"]


def test_create_paddleocr_reader_can_use_full_pipeline(monkeypatch):
    created = {}

    class FakePaddleOCR:
        def __init__(self, **kwargs):
            created.update(kwargs)

        def predict(self, image):
            return [{"rec_texts": ["ok"], "rec_scores": [1.0]}]

    monkeypatch.setenv("CHECKOCR2_PADDLE_MODE", "pipeline")
    monkeypatch.setitem(
        sys.modules,
        "paddleocr",
        types.SimpleNamespace(PaddleOCR=FakePaddleOCR),
    )

    reader = create_paddleocr_reader(["ko", "en"], gpu=False)

    assert created["lang"] == "korean"
    assert created["ocr_version"] == "PP-OCRv5"
    assert created["text_detection_model_name"] == "PP-OCRv5_mobile_det"
    assert created["text_recognition_model_name"] == "korean_PP-OCRv5_mobile_rec"
    assert created["use_doc_orientation_classify"] is False
    assert reader.readtext("image") == ["ok"]


def test_paddle_recognition_model_uses_korean_model_when_requested():
    assert paddle_recognition_model(["ko"]) == "korean_PP-OCRv5_mobile_rec"
    assert paddle_recognition_model(["en"]) == "en_PP-OCRv5_mobile_rec"


def test_create_paddleocr_reader_reports_import_failure(monkeypatch):
    monkeypatch.delitem(sys.modules, "paddleocr", raising=False)
    with pytest.raises(OCREngineError, match="PaddleOCR import failed"):
        create_paddleocr_reader(["en"])
