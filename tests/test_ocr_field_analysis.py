from __future__ import annotations

import pytest

from checkocr2.ocr_field_analysis import analyze_date_field, analyze_rate_field


@pytest.mark.parametrize("raw_text", ["", "   ", None])
def test_analyze_date_field_preserves_empty_text_log(raw_text):
    result = analyze_date_field(raw_text, "날짜")

    assert result.value == ""
    assert result.log_events == (("[날짜] 텍스트가 비어있습니다.", "DEBUG"),)


def test_analyze_date_field_preserves_valid_and_invalid_logs():
    valid = analyze_date_field("2026-05-08", "날짜")
    invalid = analyze_date_field("not a date", "날짜")

    assert valid.value == "2026/05/08"
    assert valid.log_events == (
        ("[날짜] 원본 텍스트: '2026-05-08'", "DEBUG"),
        ("[날짜] 유효한 날짜: '2026/05/08'", "DEBUG"),
    )
    assert invalid.value == ""
    assert invalid.log_events == (
        ("[날짜] 원본 텍스트: 'not a date'", "DEBUG"),
        ("[날짜] 유효하지 않은 날짜 형식: 'not a date' (원본: 'not a date')", "DEBUG"),
    )


def test_analyze_date_field_rejects_invalid_calendar_date():
    result = analyze_date_field("2026-02-30", "날짜")

    assert result.value == ""
    assert result.log_events == (
        ("[날짜] 원본 텍스트: '2026-02-30'", "DEBUG"),
        ("[날짜] 유효하지 않은 날짜 형식: '2026/02/30' (원본: '2026-02-30')", "DEBUG"),
    )


@pytest.mark.parametrize("raw_text", ["", "   ", None])
def test_analyze_rate_field_preserves_empty_text_log(raw_text):
    result = analyze_rate_field(raw_text, "금리")

    assert result.value == ""
    assert result.log_events == (("[금리] 텍스트가 비어있습니다.", "DEBUG"),)


def test_analyze_rate_field_preserves_valid_and_invalid_logs():
    valid = analyze_rate_field("3.5%", "금리")
    invalid = analyze_rate_field("rate", "금리")

    assert valid.value == "3.500"
    assert valid.log_events == (
        ("[금리] 원본 텍스트: '3.5%'", "DEBUG"),
        ("[금리] 유효한 금리: '3.500'", "DEBUG"),
    )
    assert invalid.value == ""
    assert invalid.log_events == (
        ("[금리] 원본 텍스트: 'rate'", "DEBUG"),
        ("[금리] 유효하지 않은 금리 형식: '' (원본: 'rate')", "DEBUG"),
    )


def test_field_analysis_log_events_are_immutable_ordered_tuples():
    result = analyze_date_field("2026-05-08")

    assert isinstance(result.log_events, tuple)
    assert all(isinstance(event, tuple) for event in result.log_events)
    assert result.log_events == (
        ("[날짜] 원본 텍스트: '2026-05-08'", "DEBUG"),
        ("[날짜] 유효한 날짜: '2026/05/08'", "DEBUG"),
    )
