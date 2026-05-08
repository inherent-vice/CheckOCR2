from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.benchmark_ocr import resolve_crop_path, validate_output_path


def test_benchmark_script_dry_run_writes_report(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text,source_run,notes\n"
        "missing.png,date,2026/05/08,unit,\n",
        encoding="utf-8",
    )
    output_json = tmp_path / "report.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_ocr.py",
            "--dry-run",
            "--fixture-csv",
            str(fixture_csv),
            "--output-json",
            str(output_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "dry_run"
    assert report["total_cases"] == 1


def test_benchmark_dry_run_requires_fixture_unless_allow_empty():
    missing = Path("tests/fixtures/ocr_crops/missing_ground_truth.csv")

    result = subprocess.run(
        [sys.executable, "scripts/benchmark_ocr.py", "--dry-run", "--fixture-csv", str(missing)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Fixture CSV not found" in result.stderr

    allowed = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_ocr.py",
            "--dry-run",
            "--allow-empty-fixture",
            "--fixture-csv",
            str(missing),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert allowed.returncode == 0


def test_benchmark_rejects_crop_paths_outside_fixture_dir(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()

    with pytest.raises(ValueError, match="escapes fixture directory"):
        resolve_crop_path(fixture_dir, "../outside.png")

    with pytest.raises(ValueError, match="must be relative"):
        resolve_crop_path(fixture_dir, str(Path.cwd() / "outside.png"))


def test_benchmark_rejects_unignored_repo_output_path():
    with pytest.raises(ValueError, match="\\.analysis_tmp"):
        validate_output_path(Path("benchmark_report.json"), allow_repo_output=False)

    validate_output_path(Path(".analysis_tmp/benchmark_report.json"), allow_repo_output=False)
