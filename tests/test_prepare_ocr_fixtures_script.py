from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from scripts.audit_ocr_fixtures import audit_fixtures
from scripts.prepare_ocr_fixtures import prepare_fixtures


def write_crop(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), "white").save(path)


def read_fixture_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_prepare_fixtures_writes_review_required_draft_csv_and_copies_crops(tmp_path):
    source_dir = tmp_path / "detail_images"
    write_crop(source_dir / "A001_date.png")
    write_crop(source_dir / "A001_rate.png")
    output_dir = tmp_path / "fixtures"

    summary = prepare_fixtures(source_dir=source_dir, output_dir=output_dir)

    assert summary["total_cases"] == 2
    assert summary["field_counts"] == {"date": 1, "rate": 1}
    rows = read_fixture_csv(output_dir / "ground_truth_draft.csv")
    assert [row["field"] for row in rows] == ["date", "rate"]
    assert rows[0]["expected_text"] == ""
    assert "review_required" in rows[0]["notes"]
    assert (output_dir / rows[0]["crop_path"]).exists()
    assert (output_dir / rows[1]["crop_path"]).exists()

    audit = audit_fixtures(
        output_dir / "ground_truth_draft.csv",
        min_total=2,
        min_by_field={"date": 1, "rate": 1},
    )
    assert audit["status"] == "not_ready"
    assert "blank expected_text for 0001_A001_date.png" in audit["errors"]
    assert (
        "draft fixture marker for 0001_A001_date.png: review_required"
        in audit["errors"]
    )


def test_prepare_fixtures_can_prefill_expected_values_from_run_report(tmp_path):
    source_dir = tmp_path / "detail_images"
    write_crop(source_dir / "A001_date.png")
    write_crop(source_dir / "A001_rate.png")
    run_report = tmp_path / "sample_run_report.json"
    run_report.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "code": "A001",
                        "date": "2026-05-11",
                        "rate": "3.5%",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "fixtures"

    prepare_fixtures(
        source_dir=source_dir,
        output_dir=output_dir,
        run_report=run_report,
        fill_expected_from_report=True,
    )

    rows = read_fixture_csv(output_dir / "ground_truth_draft.csv")
    assert rows[0]["expected_text"] == "2026/05/11"
    assert rows[1]["expected_text"] == "3.500"
    assert rows[0]["source_run"] == "sample_run_report"
    assert "expected_from_run_report" in rows[0]["notes"]

    audit = audit_fixtures(
        output_dir / "ground_truth_draft.csv",
        min_total=2,
        min_by_field={"date": 1, "rate": 1},
    )
    assert audit["status"] == "not_ready"
    assert (
        "draft fixture marker for 0001_A001_date.png: review_required"
        in audit["errors"]
    )
    assert (
        "draft fixture marker for 0001_A001_date.png: expected_from_run_report"
        in audit["errors"]
    )


def test_prepare_fixtures_requires_run_report_for_prefill(tmp_path):
    source_dir = tmp_path / "detail_images"
    write_crop(source_dir / "A001_date.png")

    with pytest.raises(ValueError, match="requires --run-report"):
        prepare_fixtures(
            source_dir=source_dir,
            output_dir=tmp_path / "fixtures",
            fill_expected_from_report=True,
        )


def test_prepare_fixtures_refuses_to_overwrite_existing_fixture_csv(tmp_path):
    source_dir = tmp_path / "detail_images"
    write_crop(source_dir / "A001_date.png")
    output_dir = tmp_path / "fixtures"
    output_dir.mkdir()
    (output_dir / "ground_truth_draft.csv").write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError, match="fixture CSV already exists"):
        prepare_fixtures(source_dir=source_dir, output_dir=output_dir)


def test_prepare_fixtures_refuses_existing_crop_collision_and_overwrites_when_requested(
    tmp_path,
):
    source_dir = tmp_path / "detail_images"
    write_crop(source_dir / "A001_date.png")
    output_dir = tmp_path / "fixtures"
    output_dir.mkdir()
    destination = output_dir / "0001_A001_date.png"
    destination.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError, match="fixture crop already exists"):
        prepare_fixtures(source_dir=source_dir, output_dir=output_dir)

    prepare_fixtures(source_dir=source_dir, output_dir=output_dir, overwrite=True)

    assert destination.read_bytes().startswith(b"\x89PNG")


def test_prepare_fixtures_rejects_csv_name_paths_and_unsafe_repo_output(tmp_path):
    source_dir = tmp_path / "detail_images"
    write_crop(source_dir / "A001_date.png")

    with pytest.raises(ValueError, match="csv_name must be a filename"):
        prepare_fixtures(
            source_dir=source_dir,
            output_dir=tmp_path / "fixtures",
            csv_name="../ground_truth.csv",
        )

    with pytest.raises(ValueError, match="ground_truth.csv is reserved"):
        prepare_fixtures(
            source_dir=source_dir,
            output_dir=tmp_path / "fixtures",
            csv_name="ground_truth.csv",
        )

    with pytest.raises(ValueError, match="output_dir must be under"):
        prepare_fixtures(
            source_dir=source_dir, output_dir=Path("docs").resolve(), dry_run=True
        )

    with pytest.raises(ValueError, match="output_dir must be under"):
        prepare_fixtures(
            source_dir=source_dir,
            output_dir=Path.home() / "CheckOCR2UnsafeFixtureOutputForTest",
            dry_run=True,
        )

    with pytest.raises(ValueError, match="source screenshot directory"):
        prepare_fixtures(source_dir=source_dir, output_dir=source_dir, dry_run=True)


def test_prepare_fixtures_dry_run_does_not_write_files(tmp_path):
    source_dir = tmp_path / "detail_images"
    write_crop(source_dir / "A001_date.png")
    output_dir = tmp_path / "fixtures"

    summary = prepare_fixtures(
        source_dir=source_dir, output_dir=output_dir, dry_run=True
    )

    assert summary["dry_run"] is True
    assert summary["total_cases"] == 1
    assert not output_dir.exists()


def test_prepare_ocr_fixtures_cli_reports_errors(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_ocr_fixtures.py",
            "--source-dir",
            str(tmp_path / "missing"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "source directory not found" in result.stderr
