from __future__ import annotations

import logging
import queue
from pathlib import Path

from PIL import Image


class DummySettings:
    def __init__(self, values=None):
        self.values = values or {}

    def get_advanced(self, key, default=None):
        return self.values.get(key, default)

    def set_advanced(self, key, value):
        self.values[key] = value


def make_workflow_manager(ocr_module):
    events = queue.Queue()
    data_manager = ocr_module.DataManager(
        app_ref=None,
        logger=logging.getLogger("tests.ocr.data"),
        message_queue=events,
    )
    manager = ocr_module.OCRWorkflowManager(
        app_ref=None,
        logger=logging.getLogger("tests.ocr.workflow"),
        message_queue=events,
        work_controller=ocr_module.WorkController(),
        settings_manager=DummySettings(),
        data_manager=data_manager,
    )
    return manager, events


def test_date_text_cleaning_characterizes_existing_formats(ocr_module):
    manager, _events = make_workflow_manager(ocr_module)

    assert manager._clean_date_text_internal("2024-05-01") == "2024/05/01"
    assert manager._clean_date_text_internal("24.05.01") == "2024/05/01"
    assert manager._clean_date_text_internal("69/12/31") == "2069/12/31"
    assert manager._clean_date_text_internal("70/01/01") == "1970/01/01"
    assert manager._clean_date_text_internal("not a date") == "not a date"


def test_rate_text_cleaning_characterizes_existing_formats(ocr_module):
    manager, _events = make_workflow_manager(ocr_module)

    assert manager._clean_rate_text_internal("3.5%") == "3.500"
    assert manager._clean_rate_text_internal("350") == "3.500"
    assert manager._clean_rate_text_internal("12,500") == "12.500"
    assert manager._clean_rate_text_internal("rate: 0.25%") == "0.250"


def test_image_upscaling_resizes_pil_images_without_ocr(ocr_module):
    manager, _events = make_workflow_manager(ocr_module)
    source = Image.new("RGB", (8, 5), "white")

    disabled = manager._apply_image_upscaling(source, False, 4.0, "LANCZOS")
    upscaled = manager._apply_image_upscaling(source, True, 2.5, "BILINEAR")

    assert disabled is source
    assert upscaled.size == (20, 12)
    assert source.size == (8, 5)


def test_capture_screenshots_saves_full_area_only_when_detail_enabled(
    ocr_module,
    monkeypatch,
    tmp_path,
):
    manager, _events = make_workflow_manager(ocr_module)
    saved_paths = []

    class FakeScreenshot:
        def __init__(self, region):
            self.region = region

        def save(self, path):
            saved_paths.append(str(path))

    monkeypatch.setattr(ocr_module, "copy_text", lambda _text: None)
    monkeypatch.setattr(ocr_module, "click", lambda *args, **kwargs: None)
    monkeypatch.setattr(ocr_module, "hotkey", lambda *args: None)
    monkeypatch.setattr(ocr_module, "screenshot", lambda region: FakeScreenshot(region))
    coords = {
        "click": (1, 1),
        "all": (0, 0, 20, 20),
        "date": (1, 2, 5, 6),
        "rate": (7, 8, 12, 13),
    }

    date_image, rate_image = manager._capture_screenshots_internal(
        "A001",
        tmp_path,
        coords,
        paste_d=0,
        load_d=0,
        save_details=False,
    )

    assert isinstance(date_image, FakeScreenshot)
    assert isinstance(rate_image, FakeScreenshot)
    assert saved_paths == []

    manager._capture_screenshots_internal(
        "A001",
        tmp_path,
        coords,
        paste_d=0,
        load_d=0,
        save_details=True,
    )

    assert [Path(path).name for path in saved_paths] == [
        "A001.png",
        "A001_date.png",
        "A001_rate.png",
    ]
