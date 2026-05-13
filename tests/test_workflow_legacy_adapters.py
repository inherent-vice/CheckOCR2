from __future__ import annotations

import pytest

from checkocr2.models import OcrRow
from checkocr2.workflow import CapturedImages, WorkflowContext
from checkocr2.workflow_legacy_adapters import LegacyAutomationAdapter, LegacyEasyOcrAdapter


def test_legacy_automation_adapter_records_capture_timing_and_returns_images():
    row_timing = {}
    capture_calls = []
    source_capture_timing = {"click_ms": 1.0, "capture_adapter_ms": 99.0}

    def capture_screenshots(stock_code, save_folder, coords, paste_delay, load_delay, save_details):
        capture_calls.append((stock_code, save_folder, coords, paste_delay, load_delay, save_details))
        return "date-image", "rate-image"

    adapter = LegacyAutomationAdapter(
        capture_screenshots,
        "out/source",
        {"click": (1, 2), "date": (3, 4, 5, 6), "rate": (7, 8, 9, 10)},
        0.5,
        2.0,
        True,
        get_capture_timing=lambda: source_capture_timing,
        row_timing_by_index=row_timing,
        elapsed_ms=lambda started: 12.5,
        now=lambda: 100.0,
    )

    result = adapter.capture(OcrRow(code="A001"), WorkflowContext(index=2, total_items=5))

    assert isinstance(result, CapturedImages)
    assert result.date_image == "date-image"
    assert result.rate_image == "rate-image"
    assert result.metadata == {"timing_ms": {"click_ms": 1.0, "capture_adapter_ms": 99.0}}
    assert row_timing == {2: {"capture_timing_ms": {"click_ms": 1.0, "capture_adapter_ms": 99.0}}}
    source_capture_timing["click_ms"] = 500.0
    assert row_timing[2]["capture_timing_ms"] == {"click_ms": 1.0, "capture_adapter_ms": 99.0}
    assert capture_calls == [
        (
            "A001",
            "out/source",
            {"click": (1, 2), "date": (3, 4, 5, 6), "rate": (7, 8, 9, 10)},
            0.5,
            2.0,
            True,
        )
    ]


@pytest.mark.parametrize(
    ("date_image", "rate_image"),
    [
        (None, "rate-image"),
        ("date-image", None),
    ],
)
def test_legacy_automation_adapter_records_timing_and_returns_none_for_missing_image(
    date_image,
    rate_image,
):
    row_timing = {}
    adapter = LegacyAutomationAdapter(
        lambda *args: (date_image, rate_image),
        "out",
        {},
        0.0,
        0.0,
        False,
        get_capture_timing=lambda: {},
        row_timing_by_index=row_timing,
        elapsed_ms=lambda started: 3.0,
        now=lambda: 1.0,
    )

    result = adapter.capture(OcrRow(code="A001"), WorkflowContext(index=0, total_items=1))

    assert result is None
    assert row_timing == {0: {"capture_timing_ms": {"capture_adapter_ms": 3.0}}}


def test_legacy_easyocr_adapter_resets_tracking_and_records_timing_and_confidence():
    row_timing = {1: {"capture_timing_ms": {"capture_adapter_ms": 2.0}}}
    row_metadata = {}
    ocr_timings = {"stale": 1.0}
    ocr_confidences = {"stale_confidence": 0.1}
    ocr_fallbacks = {"stale_fallback": 1}
    process_calls = []

    def clear_ocr_tracking():
        ocr_timings.clear()
        ocr_confidences.clear()
        ocr_fallbacks.clear()

    def process_single_ocr(date_image, rate_image, save_details):
        assert ocr_timings == {}
        assert ocr_confidences == {}
        process_calls.append((date_image, rate_image, save_details))
        ocr_timings["date_ocr_ms"] = 4.0
        ocr_timings["ocr_adapter_ms"] = 88.0
        ocr_confidences["date_confidence"] = 0.91
        ocr_fallbacks["date_fallback_count"] = 1
        return "2026/05/08", "3.500"

    adapter = LegacyEasyOcrAdapter(
        process_single_ocr,
        True,
        clear_ocr_tracking,
        get_ocr_timings=lambda: ocr_timings,
        get_ocr_confidences=lambda: ocr_confidences,
        get_ocr_fallbacks=lambda: ocr_fallbacks,
        row_timing_by_index=row_timing,
        row_metadata_by_index=row_metadata,
        elapsed_ms=lambda started: 9.5,
        now=lambda: 10.0,
    )

    result = adapter.read(
        CapturedImages("date-image", "rate-image"),
        OcrRow(code="A001"),
        WorkflowContext(index=1, total_items=2),
    )

    assert result.date == "2026/05/08"
    assert result.rate == "3.500"
    assert result.metadata == {"timing_ms": row_timing[1]}
    assert result.metadata["timing_ms"] is row_timing[1]
    assert row_timing[1]["ocr_timing_ms"] == {"date_ocr_ms": 4.0, "ocr_adapter_ms": 88.0}
    assert row_metadata == {
        1: {
            "ocr_confidence": {"date_confidence": 0.91},
            "ocr_fallback": {"date_fallback_count": 1},
        }
    }
    ocr_timings["date_ocr_ms"] = 400.0
    ocr_confidences["date_confidence"] = 0.1
    assert row_timing[1]["ocr_timing_ms"] == {"date_ocr_ms": 4.0, "ocr_adapter_ms": 88.0}
    assert row_metadata == {
        1: {
            "ocr_confidence": {"date_confidence": 0.91},
            "ocr_fallback": {"date_fallback_count": 1},
        }
    }
    assert process_calls == [("date-image", "rate-image", True)]


def test_legacy_easyocr_adapter_omits_confidence_metadata_when_empty():
    row_timing = {}
    row_metadata = {}
    adapter = LegacyEasyOcrAdapter(
        lambda *args: ("", ""),
        False,
        clear_ocr_tracking=lambda: None,
        get_ocr_timings=lambda: {},
        get_ocr_confidences=lambda: {},
        get_ocr_fallbacks=lambda: {},
        row_timing_by_index=row_timing,
        row_metadata_by_index=row_metadata,
        elapsed_ms=lambda started: 1.0,
        now=lambda: 0.0,
    )

    result = adapter.read(
        CapturedImages("date-image", "rate-image"),
        OcrRow(code="A001"),
        WorkflowContext(index=0, total_items=1),
    )

    assert result.date == ""
    assert result.rate == ""
    assert row_timing == {0: {"ocr_timing_ms": {"ocr_adapter_ms": 1.0}}}
    assert row_metadata == {}
