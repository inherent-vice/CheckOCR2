from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from scripts.run_live_smoke_with_local_simulator import (
    parse_args,
    remove_expected_outputs,
    roi_to_screen_box,
    runtime_state_value,
    validate_inputs,
    wait_for_ocr_ready,
    worker_is_alive,
)


def test_roi_to_screen_box_converts_fractional_roi_to_screen_coordinates():
    assert roi_to_screen_box((100, 200), (884, 496), (0.62, 0.0, 0.8, 0.075)) == (
        648,
        200,
        807,
        237,
    )


def test_validate_inputs_requires_manifest_paths_and_images(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (10, 10), "white").save(image_dir / "KRTEST001.png")
    manifest = {
        "smoke_input": str(tmp_path / "input.xlsx"),
        "output_dir": str(tmp_path),
        "expected_output_workbook": str(tmp_path / "input_updated.xlsx"),
        "expected_run_report": str(tmp_path / "input_run_report.json"),
        "rows": [{"code": "KRTEST001"}],
    }

    validate_inputs(manifest, image_dir)


def test_validate_inputs_rejects_missing_simulator_images(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    manifest = {
        "smoke_input": str(tmp_path / "input.xlsx"),
        "output_dir": str(tmp_path),
        "expected_output_workbook": str(tmp_path / "input_updated.xlsx"),
        "expected_run_report": str(tmp_path / "input_run_report.json"),
        "rows": [{"code": "KRTEST001"}],
    }

    with pytest.raises(FileNotFoundError, match="missing simulator images: KRTEST001"):
        validate_inputs(manifest, image_dir)


def test_remove_expected_outputs_only_deletes_declared_outputs(tmp_path: Path):
    output_workbook = tmp_path / "input_updated.xlsx"
    run_report = tmp_path / "input_run_report.json"
    keep_file = tmp_path / "keep.txt"
    for path in (output_workbook, run_report, keep_file):
        path.write_text("x", encoding="utf-8")

    remove_expected_outputs(
        {
            "smoke_input": str(tmp_path / "input.xlsx"),
            "output_dir": str(tmp_path),
            "expected_output_workbook": str(output_workbook),
            "expected_run_report": str(run_report),
        }
    )

    assert not output_workbook.exists()
    assert not run_report.exists()
    assert keep_file.exists()


def test_remove_expected_outputs_rejects_paths_outside_output_dir(tmp_path: Path):
    outside = tmp_path / "outside.xlsx"
    outside.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="expected_output_workbook must be under output_dir"):
        remove_expected_outputs(
            {
                "smoke_input": str(tmp_path / "input.xlsx"),
                "output_dir": str(tmp_path / "smoke"),
                "expected_output_workbook": str(outside),
                "expected_run_report": str(tmp_path / "smoke" / "input_run_report.json"),
            }
        )

    assert outside.exists()


def test_validate_inputs_rejects_expected_output_targeting_smoke_input(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (10, 10), "white").save(image_dir / "KRTEST001.png")
    smoke_input = tmp_path / "input.xlsx"
    manifest = {
        "smoke_input": str(smoke_input),
        "output_dir": str(tmp_path),
        "expected_output_workbook": str(smoke_input),
        "expected_run_report": str(tmp_path / "input_run_report.json"),
        "rows": [{"code": "KRTEST001"}],
    }

    with pytest.raises(ValueError, match="must not target source or smoke input workbook"):
        validate_inputs(manifest, image_dir)


def test_parse_args_accepts_required_day_dir_and_paddle_engine(tmp_path: Path):
    args = parse_args(
        [
            "--day-dir",
            str(tmp_path / "20260513"),
            "--engine",
            "paddle",
            "--overwrite",
        ]
    )

    assert args.day_dir == tmp_path / "20260513"
    assert args.engine == "paddle"
    assert args.overwrite is True


def test_worker_is_alive_accepts_property_or_method_handles():
    class PropertyWorker:
        is_alive = True

    class MethodWorker:
        def is_alive(self):
            return False

    assert worker_is_alive(PropertyWorker()) is True
    assert worker_is_alive(MethodWorker()) is False


def test_wait_for_ocr_ready_requires_runtime_ready_state(monkeypatch):
    class Workflow:
        ocr_reader = object()

    class FakeApp:
        def __init__(self):
            self.ocr_workflow_manager = Workflow()
            self.runtime_state = "OCR Loading"
            self.updates = 0

        def update(self):
            self.updates += 1
            if self.updates == 2:
                self.runtime_state = "Ready"

    app = FakeApp()
    monkeypatch.setattr("scripts.run_live_smoke_with_local_simulator.time.sleep", lambda _seconds: None)

    wait_for_ocr_ready(app, timeout_seconds=1.0)

    assert app.updates == 2
    assert runtime_state_value(app) == "Ready"
