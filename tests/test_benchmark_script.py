from __future__ import annotations

import json
import subprocess
import sys
import types
from argparse import Namespace
from pathlib import Path

import pytest
from PIL import Image

from scripts.benchmark_ocr import resolve_crop_path, run_benchmark, validate_output_path


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


def test_benchmark_report_calculates_accuracy_blank_false_positive_and_confidence(
    tmp_path,
    monkeypatch,
):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    for name in ("date.png", "blank_rate.png", "false_positive_rate.png"):
        Image.new("RGB", (8, 8), "white").save(fixture_dir / name)
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text\n"
        "date.png,date,2026/05/08\n"
        "blank_rate.png,rate,3.500\n"
        "false_positive_rate.png,rate,\n",
        encoding="utf-8",
    )
    outputs = iter(
        [
            [(None, "2026-05-08", 0.9)],
            [],
            [(None, "7.25", 0.5)],
        ]
    )

    class FakeReader:
        def __init__(self, languages, gpu=False):
            self.languages = languages
            self.gpu = gpu

        def readtext(self, image, detail=0):
            return next(outputs)

    monkeypatch.setitem(sys.modules, "easyocr", types.SimpleNamespace(Reader=FakeReader))

    report = run_benchmark(
        Namespace(
            fixture_csv=fixture_csv,
            limit=0,
            allow_empty_fixture=False,
            dry_run=False,
            gpu=False,
            detail=1,
            upscale_factor=1.0,
            upscale_method="LANCZOS",
        )
    )

    assert report["status"] == "ok"
    assert report["evaluated_cases"] == 3
    assert report["exact_accuracy"] == pytest.approx(1 / 3)
    assert report["blank_count"] == 1
    assert report["false_positive_count"] == 1
    assert report["p95_latency_ms"] >= 0
    assert report["results"][0]["confidence"] == pytest.approx(0.9)
    assert report["results"][1]["confidence"] is None
    assert report["results"][2]["confidence"] == pytest.approx(0.5)
