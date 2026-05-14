from __future__ import annotations

import pytest

from checkocr2.ocr_field_analysis import analyze_date_field, analyze_rate_field


@pytest.mark.parametrize("raw_text", ["", "   ", None])
def test_analyze_date_field_preserves_empty_text_log(raw_text):
    result = analyze_date_field(raw_text, "date")

    assert result.value == ""
    assert result.log_events == (("[date] 텍스트가 비어있습니다.", "DEBUG"),)


def test_analyze_date_field_preserves_valid_and_invalid_logs():
    valid = analyze_date_field("2026-05-08", "date")
    invalid = analyze_date_field("not a date", "date")

    assert valid.value == "2026/05/08"
    assert valid.log_events == (
        ("[date] 원본 텍스트: '2026-05-08'", "DEBUG"),
        ("[date] 유효한 날짜: '2026/05/08'", "DEBUG"),
    )
    assert invalid.value == ""
    assert invalid.log_events == (
        ("[date] 원본 텍스트: 'not a date'", "DEBUG"),
        ("[date] 유효하지 않은 날짜 형식: 'not a date' (원본: 'not a date')", "DEBUG"),
    )


def test_analyze_date_field_rejects_invalid_calendar_date():
    result = analyze_date_field("2026-02-30", "date")

    assert result.value == ""
    assert result.log_events == (
        ("[date] 원본 텍스트: '2026-02-30'", "DEBUG"),
        ("[date] 유효하지 않은 날짜 형식: '2026/02/30' (원본: '2026-02-30')", "DEBUG"),
    )


@pytest.mark.parametrize("raw_text", ["", "   ", None])
def test_analyze_rate_field_preserves_empty_text_log(raw_text):
    result = analyze_rate_field(raw_text, "rate")

    assert result.value == ""
    assert result.log_events == (("[rate] 텍스트가 비어있습니다.", "DEBUG"),)


def test_analyze_rate_field_preserves_valid_and_invalid_logs():
    valid = analyze_rate_field("3.5%", "rate")
    invalid = analyze_rate_field("rate", "rate")

    assert valid.value == "3.500"
    assert valid.log_events == (
        ("[rate] 원본 텍스트: '3.5%'", "DEBUG"),
        ("[rate] 유효한 금리: '3.500'", "DEBUG"),
    )
    assert invalid.value == ""
    assert invalid.log_events == (
        ("[rate] 원본 텍스트: 'rate'", "DEBUG"),
        ("[rate] 유효하지 않은 금리 형식: '' (원본: 'rate')", "DEBUG"),
    )


def test_analyze_rate_field_honors_custom_precision():
    result = analyze_rate_field("3.5%", "rate", precision=4)

    assert result.value == "3.5000"
    assert result.log_events == (
        ("[rate] 원본 텍스트: '3.5%'", "DEBUG"),
        ("[rate] 유효한 금리: '3.5000'", "DEBUG"),
    )


def test_field_analysis_log_events_are_immutable_ordered_tuples():
    result = analyze_date_field("2026-05-08", "date")

    assert isinstance(result.log_events, tuple)
    assert all(isinstance(event, tuple) for event in result.log_events)
    assert result.log_events == (
        ("[date] 원본 텍스트: '2026-05-08'", "DEBUG"),
        ("[date] 유효한 날짜: '2026/05/08'", "DEBUG"),
    )
