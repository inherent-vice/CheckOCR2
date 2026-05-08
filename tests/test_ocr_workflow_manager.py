from __future__ import annotations

import logging
import queue

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
