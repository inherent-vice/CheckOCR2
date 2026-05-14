from __future__ import annotations

import json
import subprocess
import sys

from PIL import Image

from scripts.audit_ocr_fixtures import audit_fixtures


def write_crop(path):
    Image.new("RGB", (12, 8), "white").save(path)


def test_audit_fixtures_accepts_minimum_date_and_rate_cases(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    write_crop(fixture_dir / "date.png")
    write_crop(fixture_dir / "rate.png")
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text,source_run,notes\n"
        "date.png,date,2026/05/08,manual,\n"
        "rate.png,rate,3.500,manual,\n",
        encoding="utf-8",
    )

    report = audit_fixtures(
        fixture_csv, min_total=2, min_by_field={"date": 1, "rate": 1}
    )

    assert report["status"] == "ready"
    assert report["ready_for_baseline"] is True
    assert report["total_cases"] == 2
    assert report["field_counts"] == {"date": 1, "rate": 1}
    assert report["image_size"]["min_width"] == 12
    assert report["image_size"]["min_height"] == 8


def test_audit_fixtures_accepts_integer_rate_expected_text(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    write_crop(fixture_dir / "rate.png")
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text,source_run,notes\n"
        "rate.png,rate,7,manual,\n",
        encoding="utf-8",
    )

    report = audit_fixtures(
        fixture_csv, min_total=1, min_by_field={"date": 0, "rate": 1}
    )

    assert report["status"] == "ready"
    assert report["ready_for_baseline"] is True
    assert report["errors"] == []


def test_audit_fixtures_reports_missing_duplicate_and_threshold_errors(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    write_crop(fixture_dir / "date.png")
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text\n"
        "date.png,date,20260508\n"
        "date.png,date,2026/05/08\n"
        "missing.png,rate,3.500\n",
        encoding="utf-8",
    )

    report = audit_fixtures(
        fixture_csv, min_total=4, min_by_field={"date": 2, "rate": 2}
    )

    assert report["status"] == "not_ready"
    assert report["ready_for_baseline"] is False
    assert "duplicate crop_path: date.png" in report["errors"]
    assert "missing crop file: missing.png" in report["errors"]
    assert "minimum total cases not met: 3 < 4" in report["errors"]
    assert "minimum rate cases not met: 1 < 2" in report["errors"]
    assert (
        "expected_text is not normalized for date.png: 20260508 -> 2026/05/08"
        in report["errors"]
    )


def test_audit_fixtures_detects_duplicate_resolved_crop_paths(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    write_crop(fixture_dir / "date.png")
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text\n"
        "date.png,date,2026/05/08\n"
        "./date.png,rate,3.500\n",
        encoding="utf-8",
    )

    report = audit_fixtures(
        fixture_csv, min_total=2, min_by_field={"date": 1, "rate": 1}
    )

    assert report["status"] == "not_ready"
    assert "duplicate crop file: ./date.png resolves to date.png" in report["errors"]


def test_audit_fixtures_rejects_blank_expected_and_draft_markers(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    write_crop(fixture_dir / "date.png")
    write_crop(fixture_dir / "rate.png")
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text,source_run,notes\n"
        "date.png,date,,draft,source=date.png; review_required\n"
        "rate.png,rate,3.500,draft,expected_from_run_report\n",
        encoding="utf-8",
    )

    report = audit_fixtures(
        fixture_csv, min_total=2, min_by_field={"date": 1, "rate": 1}
    )

    assert report["status"] == "not_ready"
    assert "blank expected_text for date.png" in report["errors"]
    assert "draft fixture marker for date.png: review_required" in report["errors"]
    assert (
        "draft fixture marker for rate.png: expected_from_run_report"
        in report["errors"]
    )


def test_audit_fixtures_cli_writes_json_and_fails_when_not_ready(tmp_path):
    fixture_csv = tmp_path / "missing.csv"
    output_json = tmp_path / "fixture_audit.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_ocr_fixtures.py",
            "--fixture-csv",
            str(fixture_csv),
            "--output-json",
            str(output_json),
            "--min-total",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "not_ready"
    assert "Fixture CSV not found" in report["errors"][0]
