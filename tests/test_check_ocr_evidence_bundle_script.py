from __future__ import annotations

import json
import subprocess
import sys

from scripts.check_ocr_evidence_bundle import check_evidence_bundle


def ready_audit():
    return {
        "fixture_csv": "tests/fixtures/ocr_crops/ground_truth.csv",
        "status": "ready",
        "ready_for_baseline": True,
        "total_cases": 100,
        "field_counts": {"date": 50, "rate": 50},
        "errors": [],
    }


def ok_benchmark():
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


def ok_matrix():
    candidate = {
        "key": "detail=0;factor=1.0;method=BILINEAR;allowlist=none",
        "status": "ok",
        "total_cases": 100,
        "evaluated_cases": 100,
        "missing_cases": 0,
        "invalid_path_cases": 0,
        "exact_accuracy": 1.0,
        "blank_on_expected_nonempty_count": 0,
        "false_positive_count": 0,
        "p95_latency_ms": 12.3,
        "field_summaries": ok_benchmark()["field_summaries"],
    }
    field_flags = {
        "coverage_unchanged": True,
        "accuracy_not_regressed": True,
        "blank_not_increased": True,
        "false_positive_not_increased": True,
        "p95_latency_not_increased": True,
    }
    return {
        "fixture_csv": "tests/fixtures/ocr_crops/ground_truth.csv",
        "dry_run": False,
        "total_candidates": 1,
        "baseline": candidate,
        "candidates": [candidate],
        "comparisons": [
            {
                "key": candidate["key"],
                "against_baseline": {
                    **field_flags,
                    "field_comparisons": {
                        "date": field_flags,
                        "rate": field_flags,
                    },
                },
            }
        ],
    }


def ok_live_comparison():
    return {
        "status": "ok",
        "accepted": True,
        "gates": {
            "same_input": True,
            "outputs_unchanged": True,
            "blank_not_increased": True,
            "failure_not_increased": True,
            "timing_values_valid": True,
            "p95_improvement_met": True,
        },
    }


def test_check_evidence_bundle_accepts_real_artifacts_with_live_comparison():
    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        live_comparison_report=ok_live_comparison(),
        require_live_comparison=True,
    )

    assert report["status"] == "ready"
    assert report["accepted"] is True
    assert report["errors"] == []


def test_check_evidence_bundle_rejects_bootstrap_artifacts():
    benchmark = {**ok_benchmark(), "status": "dry_run", "dry_run": True, "total_cases": 0}
    matrix = {**ok_matrix(), "dry_run": True, "total_candidates": 0}
    audit = {**ready_audit(), "status": "not_ready", "ready_for_baseline": False}

    report = check_evidence_bundle(
        audit_report=audit,
        benchmark_report=benchmark,
        matrix_report=matrix,
    )

    assert report["accepted"] is False
    assert "fixture audit is not ready" in report["errors"]
    assert "benchmark is a dry-run artifact" in report["errors"]
    assert "matrix is a dry-run artifact" in report["errors"]
    assert "matrix total_candidates must be greater than zero" in report["errors"]


def test_check_evidence_bundle_reports_concise_matrix_dry_run_error():
    matrix = {**ok_matrix(), "dry_run": True}

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=matrix,
    )

    matrix_errors = report["checks"]["matrix"]["errors"]
    assert matrix_errors == ["matrix is a dry-run artifact"]
    assert report["accepted"] is False


def test_check_evidence_bundle_warns_on_exploratory_matrix_regressions():
    matrix = ok_matrix()
    matrix["comparisons"][0]["against_baseline"]["accuracy_not_regressed"] = False
    matrix["comparisons"][0]["against_baseline"]["field_comparisons"]["rate"][
        "blank_not_increased"
    ] = False

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=matrix,
    )

    assert report["accepted"] is True
    assert any("failed accuracy_not_regressed" in warning for warning in report["warnings"])
    assert any(
        "field rate failed blank_not_increased" in warning
        for warning in report["warnings"]
    )


def test_check_evidence_bundle_can_require_no_matrix_regressions():
    matrix = ok_matrix()
    matrix["comparisons"][0]["against_baseline"]["accuracy_not_regressed"] = False

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=matrix,
        require_no_matrix_regressions=True,
    )

    assert report["accepted"] is False
    assert any("failed accuracy_not_regressed" in error for error in report["errors"])


def test_check_evidence_bundle_requires_live_comparison_when_requested():
    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        require_live_comparison=True,
    )

    assert report["accepted"] is False
    assert "live comparison is required but missing" in report["errors"]


def test_check_evidence_bundle_rejects_mixed_fixture_artifacts():
    benchmark = {**ok_benchmark(), "total_cases": 1}
    matrix = ok_matrix()
    matrix["fixture_csv"] = "tests/fixtures/other/ground_truth.csv"

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=benchmark,
        matrix_report=matrix,
    )

    assert report["accepted"] is False
    assert "benchmark total_cases does not match fixture audit: 1 != 100" in report["errors"]
    assert "matrix fixture_csv does not match fixture audit" in report["errors"]


def test_check_ocr_evidence_bundle_cli_writes_failure_json(tmp_path):
    audit_path = tmp_path / "audit.json"
    benchmark_path = tmp_path / "benchmark.json"
    matrix_path = tmp_path / "matrix.json"
    output_path = tmp_path / "bundle.json"
    audit_path.write_text(json.dumps(ready_audit()), encoding="utf-8")
    benchmark_path.write_text(json.dumps(ok_benchmark()), encoding="utf-8")
    matrix_path.write_text(json.dumps({**ok_matrix(), "dry_run": True}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_ocr_evidence_bundle.py",
            "--audit-json",
            str(audit_path),
            "--benchmark-json",
            str(benchmark_path),
            "--matrix-json",
            str(matrix_path),
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
    assert "matrix is a dry-run artifact" in report["errors"]
