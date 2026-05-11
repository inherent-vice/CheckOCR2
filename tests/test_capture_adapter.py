from __future__ import annotations

from pathlib import Path

from checkocr2.capture_adapter import capture_screenshots


class FakeLoggerQueue:
    def __init__(self):
        self.events = []

    def put(self, event):
        self.events.append(event)


class FakeSettings:
    def get_advanced(self, key, default=None):
        assert key == "click_interval"
        return default


class FakeStopEvent:
    def __init__(self, stop_on_call: int | None = None):
        self.stop_on_call = stop_on_call
        self.calls = 0

    def wait(self, timeout):
        self.calls += 1
        return self.stop_on_call == self.calls


class FakeWorkController:
    def __init__(self, *, stopped=False, stop_on_wait: int | None = None):
        self.is_stopped = stopped
        self.stop_event = FakeStopEvent(stop_on_wait)


class FakeScreenshot:
    def __init__(self, region, saved_paths):
        self.region = region
        self.saved_paths = saved_paths

    def save(self, path):
        self.saved_paths.append(str(path))


def valid_coords():
    return {
        "click": (1, 1),
        "all": (0, 0, 20, 20),
        "date": (1, 2, 5, 6),
        "rate": (7, 8, 12, 13),
    }


def test_capture_without_details_captures_only_date_and_rate(tmp_path):
    saved_paths = []
    captured_regions = []
    calls = []

    def screenshot_func(region):
        captured_regions.append(region)
        return FakeScreenshot(region, saved_paths)

    result = capture_screenshots(
        "A001",
        tmp_path,
        valid_coords(),
        paste_d=0,
        load_d=0,
        save_details=False,
        work_controller=FakeWorkController(),
        settings_manager=FakeSettings(),
        message_queue=FakeLoggerQueue(),
        copy_text_func=lambda text: calls.append(("copy", text)),
        click_func=lambda *args, **kwargs: calls.append(("click", args, kwargs)),
        hotkey_func=lambda *keys: calls.append(("hotkey", keys)),
        screenshot_func=screenshot_func,
    )

    assert result.date_image.region == (1, 2, 4, 4)
    assert result.rate_image.region == (7, 8, 5, 5)
    assert captured_regions == [(1, 2, 4, 4), (7, 8, 5, 5)]
    assert saved_paths == []
    assert calls[0] == ("copy", "A001")
    assert calls[-1] == ("hotkey", ("ctrl", "v"))
    assert result.timing_ms["capture_all_ms"] == 0.0
    assert result.timing_ms["save_all_ms"] == 0.0
    assert "capture_total_ms" in result.timing_ms


def test_capture_with_details_saves_all_date_and_rate_images(tmp_path):
    saved_paths = []
    captured_regions = []

    def screenshot_func(region):
        captured_regions.append(region)
        return FakeScreenshot(region, saved_paths)

    result = capture_screenshots(
        "A/001",
        tmp_path,
        valid_coords(),
        paste_d=0,
        load_d=0,
        save_details=True,
        work_controller=FakeWorkController(),
        settings_manager=FakeSettings(),
        message_queue=FakeLoggerQueue(),
        copy_text_func=lambda _text: None,
        click_func=lambda *args, **kwargs: None,
        hotkey_func=lambda *keys: None,
        screenshot_func=screenshot_func,
    )

    assert result.date_image == str(Path(tmp_path) / "A_001_date.png")
    assert result.rate_image == str(Path(tmp_path) / "A_001_rate.png")
    assert [Path(path).name for path in saved_paths] == [
        "A_001.png",
        "A_001_date.png",
        "A_001_rate.png",
    ]
    assert captured_regions == [(0, 0, 20, 20), (1, 2, 4, 4), (7, 8, 5, 5)]


def test_capture_returns_empty_result_when_already_stopped(tmp_path):
    result = capture_screenshots(
        "A001",
        tmp_path,
        valid_coords(),
        paste_d=0,
        load_d=0,
        save_details=False,
        work_controller=FakeWorkController(stopped=True),
        settings_manager=FakeSettings(),
        message_queue=FakeLoggerQueue(),
        copy_text_func=lambda _text: (_ for _ in ()).throw(AssertionError("no copy")),
        click_func=lambda *args, **kwargs: None,
        hotkey_func=lambda *keys: None,
        screenshot_func=lambda region: None,
    )

    assert result.date_image is None
    assert result.rate_image is None
    assert set(result.timing_ms) == {"capture_total_ms"}


def test_capture_returns_empty_result_when_stopped_during_paste_wait(tmp_path):
    calls = []

    result = capture_screenshots(
        "A001",
        tmp_path,
        valid_coords(),
        paste_d=1,
        load_d=0,
        save_details=False,
        work_controller=FakeWorkController(stop_on_wait=1),
        settings_manager=FakeSettings(),
        message_queue=FakeLoggerQueue(),
        copy_text_func=lambda text: calls.append(("copy", text)),
        click_func=lambda *args, **kwargs: calls.append(("click", args, kwargs)),
        hotkey_func=lambda *keys: calls.append(("hotkey", keys)),
        screenshot_func=lambda region: None,
    )

    assert result.date_image is None
    assert result.rate_image is None
    assert [call[0] for call in calls] == ["copy", "click"]
    assert "paste_wait_ms" in result.timing_ms
    assert "capture_total_ms" in result.timing_ms


def test_capture_returns_empty_result_when_stopped_during_load_wait(tmp_path):
    calls = []

    result = capture_screenshots(
        "A001",
        tmp_path,
        valid_coords(),
        paste_d=0,
        load_d=1,
        save_details=False,
        work_controller=FakeWorkController(stop_on_wait=2),
        settings_manager=FakeSettings(),
        message_queue=FakeLoggerQueue(),
        copy_text_func=lambda text: calls.append(("copy", text)),
        click_func=lambda *args, **kwargs: calls.append(("click", args, kwargs)),
        hotkey_func=lambda *keys: calls.append(("hotkey", keys)),
        screenshot_func=lambda region: calls.append(("screenshot", region)),
    )

    assert result.date_image is None
    assert result.rate_image is None
    assert [call[0] for call in calls] == ["copy", "click", "hotkey"]
    assert "load_wait_ms" in result.timing_ms
    assert "capture_total_ms" in result.timing_ms


def test_capture_invalid_all_area_logs_error_and_stops(tmp_path):
    queue = FakeLoggerQueue()
    coords = valid_coords()
    coords["all"] = (5, 5, 1, 1)

    result = capture_screenshots(
        "A001",
        tmp_path,
        coords,
        paste_d=0,
        load_d=0,
        save_details=False,
        work_controller=FakeWorkController(),
        settings_manager=FakeSettings(),
        message_queue=queue,
        copy_text_func=lambda _text: None,
        click_func=lambda *args, **kwargs: None,
        hotkey_func=lambda *keys: None,
        screenshot_func=lambda region: (_ for _ in ()).throw(AssertionError("no capture")),
    )

    assert result.date_image is None
    assert result.rate_image is None
    assert queue.events == [("log", "[A001] 전체 영역 좌표 오류: (5, 5, 1, 1)", "ERROR")]


def test_capture_invalid_date_area_logs_error_and_still_captures_rate(tmp_path):
    queue = FakeLoggerQueue()
    coords = valid_coords()
    coords["date"] = (5, 5, 1, 1)

    result = capture_screenshots(
        "A001",
        tmp_path,
        coords,
        paste_d=0,
        load_d=0,
        save_details=False,
        work_controller=FakeWorkController(),
        settings_manager=FakeSettings(),
        message_queue=queue,
        copy_text_func=lambda _text: None,
        click_func=lambda *args, **kwargs: None,
        hotkey_func=lambda *keys: None,
        screenshot_func=lambda region: FakeScreenshot(region, []),
    )

    assert result.date_image is None
    assert result.rate_image.region == (7, 8, 5, 5)
    assert queue.events == [("log", "[A001] 날짜 영역 좌표 오류: (5, 5, 1, 1)", "ERROR")]
