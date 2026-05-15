from __future__ import annotations

import pytest

from checkocr2.exceptions import OCREngineError
from checkocr2.ocr_engine import (
    OCR_ENGINE_EASYOCR,
    OCR_ENGINE_PADDLE,
    BlankFallbackOcrReader,
    confidence_is_accepted,
    create_ocr_reader,
    default_ocr_languages,
    extract_text_with_confidence,
    normalize_confidence_threshold,
    normalize_ocr_engine,
    read_ocr_text,
    reader_engine_metadata,
)


class FakeReader:
    def __init__(self):
        self.calls = []

    def readtext(self, image, detail=0, **kwargs):
        self.calls.append((image, detail, kwargs))
        return ["2026/05/08"]


def test_read_ocr_text_delegates_to_reader_with_detail():
    reader = FakeReader()

    result = read_ocr_text(reader, "image-array", detail=1)

    assert result == ["2026/05/08"]
    assert reader.calls == [("image-array", 1, {})]


def test_read_ocr_text_passes_allowlist_only_when_requested():
    reader = FakeReader()

    read_ocr_text(reader, "image-array", detail=0, allowlist="0123456789")

    assert reader.calls == [("image-array", 0, {"allowlist": "0123456789"})]


def test_read_ocr_text_normalizes_reader_failures():
    class FailingReader:
        def readtext(self, image, detail=0, **kwargs):
            raise RuntimeError("opencv failed")

    with pytest.raises(OCREngineError, match="readtext failed"):
        read_ocr_text(FailingReader(), "image-array")


def test_blank_fallback_reader_uses_primary_when_text_exists():
    class Reader:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def readtext(self, image, detail=0, **kwargs):
            self.calls.append((image, detail, kwargs))
            return self.result

    primary = Reader(["2026/05/08"])
    fallback = Reader(["fallback"])
    reader = BlankFallbackOcrReader(primary, fallback)

    assert reader.readtext("image", detail=0, allowlist="0123") == ["2026/05/08"]
    assert primary.calls == [("image", 0, {"allowlist": "0123"})]
    assert fallback.calls == []
    assert reader.fallback_count == 0


def test_blank_fallback_reader_retries_when_primary_is_blank():
    class Reader:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def readtext(self, image, detail=0, **kwargs):
            self.calls.append((image, detail, kwargs))
            return self.result

    primary = Reader(["   "])
    fallback = Reader(["3.500"])
    reader = BlankFallbackOcrReader(primary, fallback)

    assert reader.readtext("image-array", detail=0) == ["3.500"]
    assert primary.calls == [("image-array", 0, {})]
    assert fallback.calls == [("image-array", 0, {})]
    assert reader.fallback_count == 1


def test_blank_fallback_reader_loads_fallback_lazily_only_when_needed():
    class Reader:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def readtext(self, image, detail=0, **kwargs):
            self.calls.append((image, detail, kwargs))
            return self.result

    loaded = []
    primary = Reader([""])

    def fallback_factory():
        loaded.append("called")
        return Reader(["3.500"])

    reader = BlankFallbackOcrReader(primary, fallback_factory=fallback_factory)

    assert reader.fallback_loaded is False
    assert reader.fallback_load_count == 0
    assert reader.readtext("image-array", detail=0) == ["3.500"]
    assert loaded == ["called"]
    assert reader.fallback_loaded is True
    assert reader.fallback_load_count == 1
    assert reader.fallback_init_ms is not None


def test_reader_engine_metadata_reports_paddle_fallback_state():
    reader = BlankFallbackOcrReader(object(), object())
    reader.fallback_count = 2

    assert reader_engine_metadata(reader) == {
        "actual_ocr_engine": "paddle",
        "ocr_fallback_enabled": True,
        "ocr_fallback_engine": "easyocr",
        "ocr_fallback_count": 2,
        "ocr_fallback_loaded": True,
        "ocr_fallback_load_count": 1,
        "ocr_fallback_init_ms": None,
    }


def test_extract_text_with_confidence_handles_easyocr_detail_modes():
    assert extract_text_with_confidence(["2026", "05", "08"], 0) == ("2026 05 08", None)

    text, confidence = extract_text_with_confidence(
        [
            (None, "2026-05-08", 0.9),
            (None, "ignored-confidence", "bad"),
            (None, "3.5", 0.7),
        ],
        1,
    )

    assert text == "2026-05-08 ignored-confidence 3.5"
    assert confidence == pytest.approx(0.8)


def test_confidence_threshold_accepts_fraction_and_percent_values():
    assert normalize_confidence_threshold("80") == pytest.approx(0.8)
    assert normalize_confidence_threshold(0.25) == pytest.approx(0.25)
    assert normalize_confidence_threshold("invalid") == 0.0
    assert confidence_is_accepted(None, 0.0) is True
    assert confidence_is_accepted(0.79, 80) is False
    assert confidence_is_accepted(0.8, 80) is True


def test_normalize_ocr_engine_accepts_supported_names():
    assert normalize_ocr_engine("") == OCR_ENGINE_EASYOCR
    assert normalize_ocr_engine(" EASYOCR ") == OCR_ENGINE_EASYOCR
    assert normalize_ocr_engine("paddle") == OCR_ENGINE_PADDLE
    assert normalize_ocr_engine("paddleocr") == OCR_ENGINE_PADDLE
    with pytest.raises(OCREngineError, match="unsupported OCR engine"):
        normalize_ocr_engine("tesseract")


def test_default_ocr_languages_uses_korean_paddle_model_language():
    assert default_ocr_languages(OCR_ENGINE_EASYOCR) == ["en"]
    assert default_ocr_languages(OCR_ENGINE_PADDLE) == ["ko", "en"]


def test_create_ocr_reader_dispatches_to_requested_factory():
    calls = []

    def easy_factory(languages, *, gpu=False):
        calls.append(("easy", list(languages), gpu))
        return "easy-reader"

    def paddle_factory(languages, *, gpu=False):
        calls.append(("paddle", list(languages), gpu))
        return "paddle-reader"

    assert (
        create_ocr_reader(
            OCR_ENGINE_EASYOCR,
            ["en"],
            gpu=False,
            easyocr_factory=easy_factory,
            paddle_factory=paddle_factory,
        )
        == "easy-reader"
    )
    assert (
        create_ocr_reader(
            OCR_ENGINE_PADDLE,
            ["en"],
            gpu=True,
            easyocr_factory=easy_factory,
            paddle_factory=paddle_factory,
        )
        == "paddle-reader"
    )
    assert calls == [("easy", ["en"], False), ("paddle", ["en"], True)]
