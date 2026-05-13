from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from checkocr2.excel_io import export_grid_rows, load_grid_rows
from checkocr2.models import DATE_COL, RATE_COL, STATUS_COL, STATUS_DONE
from checkocr2.run_report import (
    create_run_report,
    finalize_run_report,
    record_row_reports,
    write_run_report,
)
from scripts.check_live_smoke_workspace import (
    check_live_smoke_workspace,
    has_nonblank_ocr_result,
)
from scripts.prepare_live_smoke_workspace import prepare_live_smoke_workspace


def write_source_workbook(path: Path) -> None:
    pd.DataFrame(
        [
            {"code": "A001", "name": "Alpha"},
            {"code": "A002", "name": "Beta"},
        ]
    ).to_excel(path, index=False)


def prepare_completed_smoke(tmp_path: Path) -> Path:
    source = tmp_path / "source.xlsx"
    write_source_workbook(source)
    output_dir = tmp_path / "live_smoke"
    manifest = prepare_live_smoke_workspace(
        source_excel=source,
        output_dir=output_dir,
        rows=2,
    )
    manifest_path = Path(manifest["manifest_path"])
    smoke_input = Path(manifest["smoke_input"])
    output_workbook = Path(manifest["expected_output_workbook"])
    run_report = Path(manifest["expected_run_report"])

    rows, _missing = load_grid_rows(smoke_input)
    for row in rows:
        row[DATE_COL] = "2026/05/12"
        row[RATE_COL] = "3.500"
        row[STATUS_COL] = STATUS_DONE
    export_grid_rows(rows, output_workbook)

    report = create_run_report(
        output_dir=str(output_dir),
        input_excel_path=str(smoke_input),
        total_items=len(rows),
        save_detail_images=True,
    )
    record_row_reports(
        report,
        rows,
        {index: {"row_total_ms": 1000 + index} for index, _row in enumerate(rows)},
    )
    finalize_run_report(
        report,
        rows,
        processed_count=len(rows),
        total_items=len(rows),
        stopped=False,
        output_workbook_path=output_workbook,
        export_timing_ms={"export_ms": 10.0},
    )
    write_run_report(report, run_report)
    return manifest_path


def test_check_live_smoke_workspace_accepts_completed_smoke(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)

    report = check_live_smoke_workspace(manifest_path, min_processed=2)

    assert report["accepted"] is True
    assert report["status"] == "ok"
    assert report["errors"] == []


def test_check_live_smoke_workspace_rejects_missing_run_artifacts(tmp_path):
    source = tmp_path / "source.xlsx"
    write_source_workbook(source)
    manifest = prepare_live_smoke_workspace(
        source_excel=source,
        output_dir=tmp_path / "live_smoke",
    )

    report = check_live_smoke_workspace(Path(manifest["manifest_path"]))

    assert report["accepted"] is False
    assert report["status"] == "not_ready"
    assert any("expected_output_workbook missing" in error for error in report["errors"])
    assert any("expected_run_report missing" in error for error in report["errors"])


def test_check_live_smoke_workspace_rejects_hash_changes(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    Path(manifest["source_excel"]).write_text("mutated", encoding="utf-8")

    report = check_live_smoke_workspace(manifest_path)

    assert report["accepted"] is False
    assert any("source_excel hash changed" in error for error in report["errors"])


def test_check_live_smoke_workspace_rejects_mismatched_report_input(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_report = Path(manifest["expected_run_report"])
    data = json.loads(run_report.read_text(encoding="utf-8"))
    data["input_excel_path"] = str(tmp_path / "other.xlsx")
    run_report.write_text(json.dumps(data), encoding="utf-8")

    report = check_live_smoke_workspace(manifest_path)

    assert report["accepted"] is False
    assert any("input_excel_path mismatch" in error for error in report["errors"])


def test_check_live_smoke_workspace_rejects_manifest_that_targets_source_workbook(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["smoke_input"] = manifest["source_excel"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = check_live_smoke_workspace(manifest_path)

    assert report["accepted"] is False
    assert any("smoke_input must not be the source_excel" in error for error in report["errors"])


def test_check_live_smoke_workspace_rejects_manifest_paths_outside_output_dir(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outside_output = tmp_path / "outside.xlsx"
    outside_output.write_text("not a workbook", encoding="utf-8")
    manifest["expected_output_workbook"] = str(outside_output)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = check_live_smoke_workspace(manifest_path)

    assert report["accepted"] is False
    assert any("expected_output_workbook must be under output_dir" in error for error in report["errors"])


def test_check_live_smoke_workspace_rejects_stopped_error_and_low_processed_reports(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_report = Path(manifest["expected_run_report"])
    data = json.loads(run_report.read_text(encoding="utf-8"))
    data["summary"]["processed_count"] = 0
    data["summary"]["stopped"] = True
    data["errors"] = ["capture failed"]
    run_report.write_text(json.dumps(data), encoding="utf-8")

    report = check_live_smoke_workspace(manifest_path, min_processed=1)

    assert report["accepted"] is False
    assert "run report processed_count too small: 0 < 1" in report["errors"]
    assert "run report indicates the smoke run was stopped" in report["errors"]
    assert "run report contains errors: capture failed" in report["errors"]


def test_check_live_smoke_workspace_rejects_all_blank_ocr_results(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_workbook = Path(manifest["expected_output_workbook"])
    run_report = Path(manifest["expected_run_report"])

    rows, _missing = load_grid_rows(output_workbook)
    for row in rows:
        row[DATE_COL] = ""
        row[RATE_COL] = ""
    export_grid_rows(rows, output_workbook)

    data = json.loads(run_report.read_text(encoding="utf-8"))
    for row in data["rows"]:
        row["date"] = ""
        row["rate"] = ""
        row["blank_fields"] = ["date", "rate"]
    data["summary"]["blank_date_count"] = len(data["rows"])
    data["summary"]["blank_rate_count"] = len(data["rows"])
    run_report.write_text(json.dumps(data), encoding="utf-8")

    report = check_live_smoke_workspace(manifest_path)

    assert report["accepted"] is False
    assert "run report has no nonblank OCR date/rate results" in report["errors"]
    assert "output workbook has no nonblank OCR date/rate results" in report["errors"]


def test_check_live_smoke_workspace_rejects_replay_artifacts_as_live_smoke(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_report = Path(manifest["expected_run_report"])
    data = json.loads(run_report.read_text(encoding="utf-8"))
    data["execution_mode"] = "real_data_replay"
    run_report.write_text(json.dumps(data), encoding="utf-8")

    report = check_live_smoke_workspace(manifest_path)

    assert report["accepted"] is False
    assert "run report is a real-data replay artifact, not a live GUI smoke" in report["errors"]


def test_has_nonblank_ocr_result_accepts_canonical_grid_columns():
    assert has_nonblank_ocr_result([{DATE_COL: "2026/05/13", RATE_COL: ""}]) is True
    assert has_nonblank_ocr_result([{DATE_COL: "", RATE_COL: "2.750"}]) is True
    assert has_nonblank_ocr_result([{DATE_COL: "", RATE_COL: ""}]) is False


def test_check_live_smoke_workspace_cli_rejects_repo_output_json(tmp_path):
    manifest_path = prepare_completed_smoke(tmp_path)
    output_json = Path("docs/live_smoke_check.json")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_live_smoke_workspace.py",
            "--manifest",
            str(manifest_path),
            "--output-json",
            str(output_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "output_json must be under .analysis_tmp, the smoke output_dir, or temp" in result.stderr
    assert not output_json.exists()


def test_check_live_smoke_workspace_cli_writes_failure_json(tmp_path):
    source = tmp_path / "source.xlsx"
    write_source_workbook(source)
    manifest = prepare_live_smoke_workspace(
        source_excel=source,
        output_dir=tmp_path / "live_smoke",
    )
    output_json = tmp_path / "live_smoke_check.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_live_smoke_workspace.py",
            "--manifest",
            manifest["manifest_path"],
            "--output-json",
            str(output_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "not_ready"
