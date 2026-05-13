from __future__ import annotations

import json
import subprocess
import sys

from scripts.check_ocr_repeatability import check_ocr_repeatability


def repeated_reports(count: int = 3) -> list[dict]:
    return [{**ok_benchmark(), "run_id": f"run-{index + 1}"} for index in range(count)]


def ok_benchmark() -> dict:
    return {
        "fixture_csv": "tests/fixtures/ocr_crops/ground_truth.csv",
        "status": "ok",
        "dry_run": False,
        "total_cases": 100,
        "evaluated_cases": 100,
        "missing_cases": 0,
        "invalid_path_cases": 0,
        "exact_accuracy": 1.0,
        "blank_on_expected_nonempty_count": 0,
        "false_positive_count": 0,
        "p95_latency_ms": 12.3,
        "settings": {
            "gpu": False,
            "detail": 0,
            "upscale_factor": 2.0,
            "upscale_method": "LANCZOS",
            "allowlist_mode": "none",
        },
        "field_summaries": {
            "date": {
                "total_cases": 50,
                "evaluated_cases": 50,
                "missing_cases": 0,
                "invalid_path_cases": 0,
                "exact_accuracy": 1.0,
                "blank_on_expected_nonempty_count": 0,
                "false_positive_count": 0,
                "p95_latency_ms": 12.0,
            },
            "rate": {
                "total_cases": 50,
                "evaluated_cases": 50,
                "missing_cases": 0,
                "invalid_path_cases": 0,
                "exact_accuracy": 1.0,
                "blank_on_expected_nonempty_count": 0,
                "false_positive_count": 0,
                "p95_latency_ms": 12.3,
            },
        },
    }


def test_check_ocr_repeatability_accepts_three_matching_reports():
    report = check_ocr_repeatability(repeated_reports())

    assert report["accepted"] is True
    assert report["status"] == "ok"
    assert report["run_count"] == 3
    assert report["fixture_csv"] == "tests/fixtures/ocr_crops/ground_truth.csv"
    assert report["errors"] == []
    assert report["latency_summary"]["p95_latency_ms"]["max"] == 12.3


def test_check_ocr_repeatability_rejects_too_few_runs_and_dry_run():
    reports = repeated_reports(2)
    reports[1] = {**reports[1], "dry_run": True, "status": "dry_run"}

    report = check_ocr_repeatability(reports)

    assert report["accepted"] is False
    assert "repeatability requires at least 3 runs: 2 provided" in report["errors"]
    assert "repeat run 2 is a dry-run artifact" in report["errors"]


def test_check_ocr_repeatability_rejects_fixture_settings_and_coverage_mismatch():
    reports = repeated_reports()
    reports[1] = {**reports[1], "fixture_csv": "tests/fixtures/other/ground_truth.csv"}
    reports[2] = {
        **reports[2],
        "settings": {**reports[2]["settings"], "detail": 1},
        "field_summaries": {
            **reports[2]["field_summaries"],
            "rate": {**reports[2]["field_summaries"]["rate"], "total_cases": 49},
        },
    }

    report = check_ocr_repeatability(reports)

    assert report["accepted"] is False
    assert "run 2 fixture_csv does not match run 1" in report["errors"]
    assert "run 3 settings do not match run 1" in report["errors"]
    assert "run 3 field rate total_cases changed: 49 != 50" in report["errors"]


def test_check_ocr_repeatability_rejects_output_metric_changes():
    reports = repeated_reports()
    reports[1] = {
        **reports[1],
        "exact_accuracy": 0.99,
        "blank_on_expected_nonempty_count": 1,
        "field_summaries": {
            **reports[1]["field_summaries"],
            "date": {
                **reports[1]["field_summaries"]["date"],
                "false_positive_count": 1,
            },
        },
    }

    report = check_ocr_repeatability(reports)

    assert report["accepted"] is False
    assert "run 2 exact_accuracy changed: 0.99 != 1.0" in report["errors"]
    assert (
        "run 2 blank_on_expected_nonempty_count changed: 1 != 0"
        in report["errors"]
    )
    assert (
        "run 2 field date false_positive_count changed: 1 != 0"
        in report["errors"]
    )


def test_check_ocr_repeatability_cli_writes_failure_json(tmp_path):
    paths = []
    for index, report in enumerate(repeated_reports(2), start=1):
        path = tmp_path / f"run_{index}.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        paths.append(path)
    output_path = tmp_path / "repeatability.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_ocr_repeatability.py",
            "--benchmark-json",
            *(str(path) for path in paths),
            "--output-json",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "not_ready"
    assert "repeatability requires at least 3 runs: 2 provided" in report["errors"]
