from __future__ import annotations

import subprocess
import sys
from argparse import Namespace

import pytest

from scripts import benchmark_ocr_matrix


def test_parse_matrix_csv_values():
    assert benchmark_ocr_matrix.parse_csv_floats("1.0, 2.5") == [1.0, 2.5]
    assert benchmark_ocr_matrix.parse_csv_ints("0,1") == [0, 1]
    assert benchmark_ocr_matrix.parse_csv_strings("bilinear,LANCZOS") == ["BILINEAR", "LANCZOS"]
    assert benchmark_ocr_matrix.parse_csv_allowlist_modes("none,FIELD") == ["none", "field"]

    with pytest.raises(SystemExit):
        benchmark_ocr_matrix.parse_args(["--details", "2"])
    with pytest.raises(SystemExit):
        benchmark_ocr_matrix.parse_args(["--allowlist-modes", "unsafe"])


def test_run_matrix_summarizes_baseline_comparisons(monkeypatch, tmp_path):
    def fake_run_benchmark(args):
        is_baseline = (
            args.detail == 0
            and args.upscale_factor == 1.0
            and args.upscale_method == "BILINEAR"
            and args.allowlist_mode == "none"
        )
        is_improved = (
            args.detail == 1
            and args.upscale_factor == 2.0
            and args.upscale_method == "LANCZOS"
            and args.allowlist_mode == "field"
        )
        return {
            "status": "ok",
            "settings": {
                "detail": args.detail,
                "upscale_factor": args.upscale_factor,
                "upscale_method": args.upscale_method,
                "allowlist_mode": args.allowlist_mode,
            },
            "total_cases": 2,
            "evaluated_cases": 2,
            "exact_accuracy": 0.5 if is_baseline else (1.0 if is_improved else 0.5),
            "blank_count": 1 if is_baseline else (0 if is_improved else 1),
            "false_positive_count": 0,
            "p95_latency_ms": 10.0 if is_baseline else (8.0 if is_improved else 12.0),
        }

    monkeypatch.setattr(benchmark_ocr_matrix, "run_benchmark", fake_run_benchmark)
    report = benchmark_ocr_matrix.run_matrix(
        Namespace(
            fixture_csv=tmp_path / "ground_truth.csv",
            output_json=tmp_path / "matrix.json",
            dry_run=False,
            allow_empty_fixture=False,
            limit=0,
            gpu=False,
            details=[0, 1],
            upscale_factors=[1.0, 2.0],
            upscale_methods=["BILINEAR", "LANCZOS"],
            allowlist_modes=["none", "field"],
        )
    )

    assert report["total_candidates"] == 16
    assert report["baseline"]["key"] == "detail=0;factor=1.0;method=BILINEAR;allowlist=none"
    assert report["comparisons"][0]["against_baseline"] == {
        "accuracy_not_regressed": True,
        "blank_not_increased": True,
        "false_positive_not_increased": True,
        "p95_latency_not_increased": True,
    }
    improved = next(
        comparison
        for comparison in report["comparisons"]
        if comparison["key"] == "detail=1;factor=2.0;method=LANCZOS;allowlist=field"
    )
    assert improved["against_baseline"] == {
        "accuracy_not_regressed": True,
        "blank_not_increased": True,
        "false_positive_not_increased": True,
        "p95_latency_not_increased": True,
    }


def test_matrix_cli_dry_run_writes_report_for_empty_fixture(tmp_path):
    output_json = tmp_path / "matrix.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_ocr_matrix.py",
            "--dry-run",
            "--allow-empty-fixture",
            "--fixture-csv",
            str(tmp_path / "missing.csv"),
            "--output-json",
            str(output_json),
            "--upscale-factors",
            "1.0",
            "--upscale-methods",
            "LANCZOS",
            "--details",
            "0",
            "--allowlist-modes",
            "field",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output_json.exists()
