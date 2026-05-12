from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ocr_pair_processing import process_ocr_image_pair


def test_process_ocr_image_pair_preserves_date_rate_order_and_labels():
    calls = []

    def extract_text(image_source, analysis_function, field_name, save_details):
        calls.append((image_source, analysis_function("raw"), field_name, save_details))
        return f"value-{field_name}"

    result = process_ocr_image_pair(
        "date-image",
        "rate-image",
        save_details=True,
        extract_text=extract_text,
        analyze_date=lambda _raw: "date-analysis",
        analyze_rate=lambda _raw: "rate-analysis",
        emit_log=lambda _message, _level: None,
        logger=SimpleNamespace(exception=lambda _message: None),
    )

    assert result == ("value-날짜", "value-금리")
    assert calls == [
        ("date-image", "date-analysis", "날짜", True),
        ("rate-image", "rate-analysis", "금리", True),
    ]


def test_process_ocr_image_pair_skips_missing_sources():
    calls = []

    result = process_ocr_image_pair(
        None,
        "rate-image",
        save_details=False,
        extract_text=lambda *args: calls.append(args) or "rate",
        analyze_date=lambda _raw: "date-analysis",
        analyze_rate=lambda _raw: "rate-analysis",
        emit_log=lambda _message, _level: None,
        logger=SimpleNamespace(exception=lambda _message: None),
    )

    assert result == ("", "rate")
    assert len(calls) == 1
    assert calls[0][0] == "rate-image"
    assert calls[0][2] == "금리"


def test_process_ocr_image_pair_logs_and_returns_blanks_on_extraction_error():
    events = []
    exceptions = []

    def fail_extract(*_args):
        raise RuntimeError("ocr failed")

    result = process_ocr_image_pair(
        "date-image",
        "rate-image",
        save_details=False,
        extract_text=fail_extract,
        analyze_date=lambda _raw: "date-analysis",
        analyze_rate=lambda _raw: "rate-analysis",
        emit_log=lambda message, level: events.append((message, level)),
        logger=SimpleNamespace(exception=exceptions.append),
    )

    assert result == ("", "")
    assert events == [("단일 OCR 처리 중 오류: ocr failed", "ERROR")]
    assert exceptions == ["단일 OCR 처리 중 예외 발생"]


def test_process_ocr_image_pair_keeps_date_when_rate_extraction_fails():
    events = []
    exceptions = []
    calls = []

    def extract_text(image_source, _analysis_function, field_name, _save_details):
        calls.append((image_source, field_name))
        if image_source == "rate-image":
            raise ValueError("rate failed")
        return "date-value"

    result = process_ocr_image_pair(
        "date-image",
        "rate-image",
        save_details=False,
        extract_text=extract_text,
        analyze_date=lambda _raw: "date-analysis",
        analyze_rate=lambda _raw: "rate-analysis",
        emit_log=lambda message, level: events.append((message, level)),
        logger=SimpleNamespace(exception=exceptions.append),
    )

    assert result == ("date-value", "")
    assert calls == [("date-image", "날짜"), ("rate-image", "금리")]
    assert events == [("단일 OCR 처리 중 오류: rate failed", "ERROR")]
    assert exceptions == ["단일 OCR 처리 중 예외 발생"]
