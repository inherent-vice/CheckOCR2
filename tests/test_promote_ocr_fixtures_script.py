from __future__ import annotations

import csv
import json
import subprocess
import sys

import pytest
from PIL import Image

from scripts.audit_ocr_fixtures import audit_fixtures
from scripts.promote_ocr_fixtures import promote_fixtures


def write_crop(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (12, 8), "white").save(path)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_reviewed_draft(fixture_dir):
    write_crop(fixture_dir / "0001_A001_date.png")
    write_crop(fixture_dir / "0002_A001_rate.png")
    draft_csv = fixture_dir / "ground_truth_draft.csv"
    draft_csv.write_text(
        "crop_path,field,expected_text,source_run,notes\n"
        "0001_A001_date.png,date,2026/05/11,run-1,manual_checked\n"
        "0002_A001_rate.png,rate,3.5000,run-1,manual_checked\n",
        encoding="utf-8",
    )
    return draft_csv


def test_promote_fixtures_writes_ground_truth_after_confirmed_review(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    draft_csv = write_reviewed_draft(fixture_dir)
    output_csv = fixture_dir / "ground_truth.csv"

    summary = promote_fixtures(
        draft_csv=draft_csv,
        output_csv=output_csv,
        reviewed_by="ocr-reviewer",
        confirm_reviewed=True,
        min_total=2,
        min_by_field={"date": 1, "rate": 1},
    )

    assert summary["status"] == "ready"
    assert summary["ready_for_baseline"] is True
    assert summary["total_cases"] == 2
    assert summary["field_counts"] == {"date": 1, "rate": 1}
    rows = read_csv(output_csv)
    assert rows[0]["notes"] == "manual_checked; reviewed_by=ocr-reviewer"
    assert rows[1]["notes"] == "manual_checked; reviewed_by=ocr-reviewer"

    audit = audit_fixtures(
        output_csv,
        min_total=2,
        min_by_field={"date": 1, "rate": 1},
    )
    assert audit["status"] == "ready"


def test_promote_fixtures_requires_explicit_review_confirmation(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    draft_csv = write_reviewed_draft(fixture_dir)

    with pytest.raises(ValueError, match="--confirm-reviewed"):
        promote_fixtures(
            draft_csv=draft_csv,
            reviewed_by="ocr-reviewer",
            confirm_reviewed=False,
            min_total=2,
            min_by_field={"date": 1, "rate": 1},
        )

    with pytest.raises(ValueError, match="reviewed_by"):
        promote_fixtures(
            draft_csv=draft_csv,
            reviewed_by=" ",
            confirm_reviewed=True,
            min_total=2,
            min_by_field={"date": 1, "rate": 1},
        )


def test_promote_fixtures_rejects_unreviewed_draft_markers_and_blanks(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    write_crop(fixture_dir / "date.png")
    write_crop(fixture_dir / "rate.png")
    draft_csv = fixture_dir / "ground_truth_draft.csv"
    draft_csv.write_text(
        "crop_path,field,expected_text,source_run,notes\n"
        "date.png,date,,draft,source=date.png; review_required\n"
        "rate.png,rate,3.500,draft,expected_from_run_report\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        promote_fixtures(
            draft_csv=draft_csv,
            reviewed_by="ocr-reviewer",
            confirm_reviewed=True,
            min_total=2,
            min_by_field={"date": 1, "rate": 1},
        )

    message = str(exc_info.value)
    assert "blank expected_text for date.png" in message
    assert "draft marker remains for date.png: review_required" in message
    assert "draft marker remains for rate.png: expected_from_run_report" in message
    assert not (fixture_dir / "ground_truth.csv").exists()


def test_promote_fixtures_rejects_output_outside_draft_directory(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    draft_csv = write_reviewed_draft(fixture_dir)

    with pytest.raises(ValueError, match="output_csv must be named ground_truth.csv"):
        promote_fixtures(
            draft_csv=draft_csv,
            output_csv=fixture_dir / "reviewed.csv",
            reviewed_by="ocr-reviewer",
            confirm_reviewed=True,
            min_total=2,
            min_by_field={"date": 1, "rate": 1},
        )

    with pytest.raises(ValueError, match="same directory"):
        promote_fixtures(
            draft_csv=draft_csv,
            output_csv=tmp_path / "other" / "ground_truth.csv",
            reviewed_by="ocr-reviewer",
            confirm_reviewed=True,
            min_total=2,
            min_by_field={"date": 1, "rate": 1},
        )


def test_promote_fixtures_requires_audit_ready_candidate(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    write_crop(fixture_dir / "date.png")
    draft_csv = fixture_dir / "ground_truth_draft.csv"
    draft_csv.write_text(
        "crop_path,field,expected_text,source_run,notes\n"
        "date.png,date,20260511,run-1,manual_checked\n"
        "missing.png,rate,3.500,run-1,manual_checked\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="promoted fixture audit failed") as exc_info:
        promote_fixtures(
            draft_csv=draft_csv,
            reviewed_by="ocr-reviewer",
            confirm_reviewed=True,
            min_total=2,
            min_by_field={"date": 1, "rate": 1},
        )

    assert "missing crop file: missing.png" in str(exc_info.value)
    assert (
        "expected_text is not normalized for date.png: 20260511 -> 2026/05/11"
        in str(exc_info.value)
    )


def test_promote_fixtures_refuses_overwrite_and_dry_run_does_not_write(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    draft_csv = write_reviewed_draft(fixture_dir)
    output_csv = fixture_dir / "ground_truth.csv"
    output_csv.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError, match="ground truth CSV already exists"):
        promote_fixtures(
            draft_csv=draft_csv,
            output_csv=output_csv,
            reviewed_by="ocr-reviewer",
            confirm_reviewed=True,
            min_total=2,
            min_by_field={"date": 1, "rate": 1},
        )

    summary = promote_fixtures(
        draft_csv=draft_csv,
        output_csv=output_csv,
        reviewed_by="ocr-reviewer",
        confirm_reviewed=True,
        dry_run=True,
        min_total=2,
        min_by_field={"date": 1, "rate": 1},
    )

    assert summary["dry_run"] is True
    assert not (fixture_dir / "ground_truth_dry_run.csv").exists()


def test_promote_ocr_fixtures_cli_writes_json(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    draft_csv = write_reviewed_draft(fixture_dir)
    output_csv = fixture_dir / "ground_truth.csv"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/promote_ocr_fixtures.py",
            "--draft-csv",
            str(draft_csv),
            "--output-csv",
            str(output_csv),
            "--reviewed-by",
            "ocr-reviewer",
            "--confirm-reviewed",
            "--min-total",
            "2",
            "--min-date",
            "1",
            "--min-rate",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["status"] == "ready"
    assert output_csv.exists()
