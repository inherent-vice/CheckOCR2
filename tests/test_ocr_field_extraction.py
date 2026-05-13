from __future__ import annotations

from types import SimpleNamespace

from PIL import Image

from checkocr2.ocr_field_extraction import extract_ocr_field_text


class FakeTimer:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 0.001
        return self.value


def get_setting(settings):
    return lambda key, default: settings.get(key, default)


def test_extract_ocr_field_text_records_confidence_timing_and_logs():
    events = []
    analyze_calls = []

    class FakeReader:
        def __init__(self):
            self.calls = []

        def readtext(self, image, detail=0, **kwargs):
            self.calls.append((image, detail, kwargs))
            return [(None, "2026-05-08", 0.91)]

    reader = FakeReader()
    timer = FakeTimer()

    result = extract_ocr_field_text(
        Image.new("RGB", (8, 8), "white"),
        reader=reader,
        field_key="date",
        field_name="날짜",
        save_details=False,
        get_advanced=get_setting({"upscaling_enabled": True, "upscaling_factor": 2.0}),
        get_detail_level=lambda: 1,
        get_min_confidence=lambda _field_key: 0.8,
        is_stopped=lambda: False,
        emit_log=lambda message, level: events.append((message, level)),
        analyze_text=lambda text, field_name: analyze_calls.append((text, field_name)) or "2026/05/08",
        apply_upscaling=lambda image, *_args: image,
        logger=SimpleNamespace(exception=lambda _message: None),
        timer=timer,
        array_factory=lambda image: ("array", image.size),
    )

    assert result.value == "2026/05/08"
    assert result.confidence == 0.91
    assert reader.calls == [(("array", (8, 8)), 1, {})]
    assert analyze_calls == [("2026-05-08", "날짜")]
    assert any("OCR 결과 (업스케일링: 2.0x LANCZOS)" in message for message, _level in events)
    assert set(result.timing_ms) == {
        "date_image_load_ms",
        "date_preprocess_ms",
        "date_ocr_ms",
        "date_parse_ms",
        "date_total_ms",
    }


def test_extract_ocr_field_text_rejects_low_confidence_before_analysis():
    events = []
    analyze_calls = []

    class FakeReader:
        def readtext(self, image, detail=0, **kwargs):
            return [(None, "2026-05-08", 0.5)]

    result = extract_ocr_field_text(
        Image.new("RGB", (8, 8), "white"),
        reader=FakeReader(),
        field_key="date",
        field_name="날짜",
        save_details=False,
        get_advanced=get_setting({"upscaling_enabled": False}),
        get_detail_level=lambda: 1,
        get_min_confidence=lambda _field_key: 0.8,
        is_stopped=lambda: False,
        emit_log=lambda message, level: events.append((message, level)),
        analyze_text=lambda text, field_name: analyze_calls.append((text, field_name)) or text,
        apply_upscaling=lambda image, *_args: image,
        logger=SimpleNamespace(exception=lambda _message: None),
        array_factory=lambda image: image,
    )

    assert result.value == ""
    assert result.confidence == 0.5
    assert analyze_calls == []
    assert any("confidence below threshold" in message for message, _level in events)


def test_extract_ocr_field_text_runs_cleanup_log_after_errors(tmp_path):
    events = []
    exceptions = []
    image_path = tmp_path / "ABC_date.png"
    Image.new("RGB", (8, 8), "white").save(image_path)

    class FailingReader:
        def readtext(self, image, detail=0, **kwargs):
            raise RuntimeError("opencv failed")

    def fake_cleanup(image_source, *, save_details, field_name):
        return SimpleNamespace(log_event=(f"cleanup {field_name}: {image_source}", "DEBUG"))

    result = extract_ocr_field_text(
        str(image_path),
        reader=FailingReader(),
        field_key="date",
        field_name="날짜",
        save_details=False,
        get_advanced=get_setting({"upscaling_enabled": False}),
        get_detail_level=lambda: 0,
        get_min_confidence=lambda _field_key: 0.0,
        is_stopped=lambda: False,
        emit_log=lambda message, level: events.append((message, level)),
        analyze_text=lambda text, field_name: text,
        apply_upscaling=lambda image, *_args: image,
        logger=SimpleNamespace(exception=exceptions.append),
        cleanup_temp_ocr_image_func=fake_cleanup,
    )

    assert result.value == ""
    assert exceptions == ["날짜 추출 중 예외 발생"]
    assert any("OCR readtext failed: opencv failed" in message for message, _level in events)
    assert (f"cleanup 날짜: {image_path}", "DEBUG") in events
