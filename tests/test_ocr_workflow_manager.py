from __future__ import annotations

import json
import logging
import queue
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from checkocr2.models import (
    CODE_COL,
    DATE_COL,
    NAME_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_DONE,
    STATUS_STOPPED,
)
from checkocr2.run_report import create_run_report


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
    assert manager._last_capture_timing["save_all_ms"] == 0.0
    assert "capture_total_ms" in manager._last_capture_timing
    assert "click_ms" in manager._last_capture_timing

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


def test_execute_workflow_writes_run_report_with_row_timing(ocr_module, monkeypatch, tmp_path):
    manager, _events = make_workflow_manager(ocr_module)
    manager.ocr_reader = object()
    manager.data_manager.excel_data = [
        {
            CODE_COL: "A001",
            NAME_COL: "Alpha",
            DATE_COL: "",
            RATE_COL: "",
            STATUS_COL: "",
        }
    ]

    class DummyVar:
        def get(self):
            return str(tmp_path / "source.xlsx")

    class DummyApp:
        input_excel_path = DummyVar()

    ocr_outputs = iter([["2026-05-08"], ["3.5"]])
    monkeypatch.setattr(ocr_module, "copy_text", lambda _text: None)
    monkeypatch.setattr(ocr_module, "click", lambda *args, **kwargs: None)
    monkeypatch.setattr(ocr_module, "hotkey", lambda *args: None)
    monkeypatch.setattr(ocr_module, "screenshot", lambda region: Image.new("RGB", (20, 20), "white"))
    monkeypatch.setattr(ocr_module, "read_ocr_text", lambda *args, **kwargs: next(ocr_outputs))
    manager.app = DummyApp()
    ui_settings = {
        "delays": {"paste": 0, "loading": 0},
        "click_point": (1, 1),
        "all_area": (0, 0, 20, 20),
        "date_area": (0, 0, 10, 10),
        "rate_area": (10, 10, 20, 20),
    }

    manager.execute_ocr_workflow_threaded(ui_settings, str(tmp_path), save_detail_images_bool=False)

    report_path = tmp_path / "source_run_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["processed_count"] == 1
    assert report["rows"][0]["date"] == "2026/05/08"
    assert report["rows"][0]["rate"] == "3.500"
    assert "capture_timing_ms" in report["rows"][0]["timing_ms"]
    assert "ocr_timing_ms" in report["rows"][0]["timing_ms"]
    assert "update_ms" in report["rows"][0]["timing_ms"]


def test_stopped_workflow_report_uses_final_stopped_status(ocr_module, monkeypatch, tmp_path):
    manager, _events = make_workflow_manager(ocr_module)
    manager.ocr_reader = object()
    manager.data_manager.excel_data = [
        {CODE_COL: "A001", NAME_COL: "Alpha", DATE_COL: "", RATE_COL: "", STATUS_COL: ""}
    ]

    class DummyVar:
        def get(self):
            return str(tmp_path / "source.xlsx")

    class DummyApp:
        input_excel_path = DummyVar()

    def stop_after_capture(*args, **kwargs):
        manager.work_controller.stop_work()
        return Image.new("RGB", (10, 10), "white"), Image.new("RGB", (10, 10), "white")

    manager.app = DummyApp()
    monkeypatch.setattr(manager, "_capture_screenshots_internal", stop_after_capture)
    ui_settings = {
        "delays": {"paste": 0, "loading": 0},
        "click_point": (1, 1),
        "all_area": (0, 0, 20, 20),
        "date_area": (0, 0, 10, 10),
        "rate_area": (10, 10, 20, 20),
    }

    manager.execute_ocr_workflow_threaded(ui_settings, str(tmp_path), save_detail_images_bool=False)

    report = json.loads((tmp_path / "source_run_report.json").read_text(encoding="utf-8"))
    assert report["summary"]["stopped"] is True
    assert report["summary"]["status_counts"] == {STATUS_STOPPED: 1}
    assert report["rows"][0]["status"] == STATUS_STOPPED


def test_finalize_export_report_records_failure_when_old_output_exists(ocr_module, monkeypatch, tmp_path):
    rows = [
        {CODE_COL: "A001", NAME_COL: "Alpha", DATE_COL: "2026/05/08", RATE_COL: "3.500", STATUS_COL: STATUS_DONE}
    ]
    manager, _events = make_workflow_manager(ocr_module)
    manager.data_manager.excel_data = rows
    manager._current_run_report = create_run_report(
        output_dir=str(tmp_path),
        input_excel_path=str(tmp_path / "source.xlsx"),
        total_items=1,
        save_detail_images=False,
    )
    manager._current_run_report["rows"] = [{"index": 0, "timing_ms": {"row_total_ms": 1.0}}]
    manager._current_run_report["summary"]["processed_count"] = 1
    manager._current_run_report_path = tmp_path / "source_run_report.json"
    stale_output = tmp_path / "source_updated.xlsx"
    stale_output.write_text("stale output", encoding="utf-8")
    errors = []
    infos = []

    dummy_app = SimpleNamespace(
        data_manager=manager.data_manager,
        logger=logging.getLogger("tests.ocr.app"),
        ocr_workflow_manager=manager,
        _finalize_processing_states=lambda: None,
        refresh_grid_ui=lambda: None,
    )

    def fail_export_grid_rows(rows, output_path):
        raise PermissionError("locked workbook")

    monkeypatch.setattr(ocr_module, "export_grid_rows", fail_export_grid_rows)
    monkeypatch.setattr(ocr_module.messagebox, "showerror", lambda title, message: errors.append((title, message)))
    monkeypatch.setattr(ocr_module.messagebox, "showinfo", lambda title, message: infos.append((title, message)))

    ocr_module.CheckCaptureOCRApp._finalize_export_and_complete(
        dummy_app,
        str(tmp_path),
        str(tmp_path / "source.xlsx"),
        "done",
    )

    report = json.loads((tmp_path / "source_run_report.json").read_text(encoding="utf-8"))
    assert "Excel export failed: locked workbook" in report["errors"]
    assert report["summary"]["export_timing_ms"]["export_ms"] >= 0
    assert errors == [("Excel export failed", "Excel export failed: locked workbook")]
    assert infos == []
