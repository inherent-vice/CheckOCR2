from __future__ import annotations

import json
import subprocess
import sys
import types
from argparse import Namespace
from pathlib import Path

import pytest
from PIL import Image

from scripts.benchmark_ocr import (
    FIELD_ALLOWLISTS,
    resolve_crop_path,
    run_benchmark,
    validate_output_path,
)


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
        [
            sys.executable,
            "scripts/benchmark_ocr.py",
            "--dry-run",
            "--fixture-csv",
            str(missing),
        ],
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


def test_benchmark_rejects_draft_fixture_markers(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    fixture_csv = fixture_dir / "ground_truth_draft.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text,source_run,notes\n"
        "date.png,date,2026/05/08,draft,source=date.png; review_required\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_ocr.py",
            "--dry-run",
            "--fixture-csv",
            str(fixture_csv),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Fixture CSV contains draft marker" in result.stderr


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

    validate_output_path(
        Path(".analysis_tmp/benchmark_report.json"), allow_repo_output=False
    )


def test_benchmark_report_calculates_accuracy_blank_false_positive_and_confidence(
    tmp_path,
    monkeypatch,
):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    for name in (
        "date.png",
        "blank_rate.png",
        "false_positive_rate.png",
        "expected_empty_blank_rate.png",
    ):
        Image.new("RGB", (8, 8), "white").save(fixture_dir / name)
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text\n"
        "date.png,date,2026/05/08\n"
        "blank_rate.png,rate,3.500\n"
        "false_positive_rate.png,rate,\n"
        "expected_empty_blank_rate.png,rate,\n",
        encoding="utf-8",
    )
    outputs = iter(
        [
            [(None, "2026-05-08", 0.9)],
            [],
            [(None, "7.25", 0.5)],
            [],
        ]
    )

    class FakeReader:
        def __init__(self, languages, gpu=False):
            self.languages = languages
            self.gpu = gpu

        def readtext(self, image, detail=0):
            return next(outputs)

    monkeypatch.setitem(
        sys.modules, "easyocr", types.SimpleNamespace(Reader=FakeReader)
    )

    report = run_benchmark(
        Namespace(
            fixture_csv=fixture_csv,
            limit=0,
            allow_empty_fixture=False,
            dry_run=False,
            engine="easyocr",
            gpu=False,
            detail=1,
            upscale_factor=1.0,
            upscale_method="LANCZOS",
            allowlist_mode="none",
        )
    )

    assert report["status"] == "ok"
    assert report["evaluated_cases"] == 4
    assert report["exact_accuracy"] == pytest.approx(2 / 4)
    assert report["blank_count"] == 2
    assert report["blank_on_expected_nonempty_count"] == 1
    assert report["false_positive_count"] == 1
    assert report["p95_latency_ms"] >= 0
    assert report["field_summaries"]["date"]["evaluated_cases"] == 1
    assert report["field_summaries"]["date"]["exact_accuracy"] == pytest.approx(1.0)
    assert report["field_summaries"]["date"]["blank_count"] == 0
    assert report["field_summaries"]["date"]["blank_on_expected_nonempty_count"] == 0
    assert report["field_summaries"]["rate"]["evaluated_cases"] == 3
    assert report["field_summaries"]["rate"]["exact_accuracy"] == pytest.approx(1 / 3)
    assert report["field_summaries"]["rate"]["blank_count"] == 2
    assert report["field_summaries"]["rate"]["blank_on_expected_nonempty_count"] == 1
    assert report["field_summaries"]["rate"]["false_positive_count"] == 1
    assert report["results"][0]["confidence"] == pytest.approx(0.9)
    assert report["results"][1]["confidence"] is None
    assert report["results"][2]["confidence"] == pytest.approx(0.5)


def test_benchmark_field_allowlist_passes_field_specific_easyocr_allowlists(
    tmp_path,
    monkeypatch,
):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    for name in ("date.png", "rate.png"):
        Image.new("RGB", (8, 8), "white").save(fixture_dir / name)
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text\n"
        "date.png,date,2026/05/08\n"
        "rate.png,rate,3.500\n",
        encoding="utf-8",
    )
    outputs = iter([["2026-05-08"], ["3.5"]])
    allowlist_calls = []

    class FakeReader:
        def __init__(self, languages, gpu=False):
            self.languages = languages
            self.gpu = gpu

        def readtext(self, image, detail=0, allowlist=None):
            allowlist_calls.append(allowlist)
            return next(outputs)

    monkeypatch.setitem(
        sys.modules, "easyocr", types.SimpleNamespace(Reader=FakeReader)
    )

    report = run_benchmark(
        Namespace(
            fixture_csv=fixture_csv,
            limit=0,
            allow_empty_fixture=False,
            dry_run=False,
            engine="easyocr",
            gpu=False,
            detail=0,
            upscale_factor=1.0,
            upscale_method="LANCZOS",
            allowlist_mode="field",
        )
    )

    assert report["status"] == "ok"
    assert report["settings"]["allowlist_mode"] == "field"
    assert allowlist_calls == [FIELD_ALLOWLISTS["date"], FIELD_ALLOWLISTS["rate"]]
    assert report["results"][0]["allowlist"] == FIELD_ALLOWLISTS["date"]
    assert report["results"][1]["allowlist"] == FIELD_ALLOWLISTS["rate"]


def test_benchmark_uses_selected_ocr_engine(tmp_path, monkeypatch):
    from scripts import benchmark_ocr

    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    Image.new("RGB", (8, 8), "white").save(fixture_dir / "date.png")
    fixture_csv = fixture_dir / "ground_truth.csv"
    fixture_csv.write_text(
        "crop_path,field,expected_text\n"
        "date.png,date,2026/05/13\n",
        encoding="utf-8",
    )
    calls = []

    class FakeReader:
        def readtext(self, image, detail=0, **kwargs):
            return ["2026-05-13"]

    def fake_create_ocr_reader(engine, languages, *, gpu=False):
        calls.append((engine, list(languages), gpu))
        return FakeReader()

    monkeypatch.setattr(benchmark_ocr, "create_ocr_reader", fake_create_ocr_reader)

    report = run_benchmark(
        Namespace(
            fixture_csv=fixture_csv,
            limit=0,
            allow_empty_fixture=False,
            dry_run=False,
            engine="paddle",
            gpu=True,
            detail=0,
            upscale_factor=1.0,
            upscale_method="LANCZOS",
            allowlist_mode="none",
        )
    )

    assert report["status"] == "ok"
    assert report["settings"]["engine"] == "paddle"
    assert calls == [("paddle", ["en"], True)]
