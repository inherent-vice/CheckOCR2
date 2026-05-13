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


def ok_live_smoke():
    return {
        "status": "ok",
        "accepted": True,
        "manifest": ".analysis_tmp/live_smoke/live_smoke_manifest.json",
        "smoke_input": ".analysis_tmp/live_smoke/live_smoke_input.xlsx",
        "expected_output_workbook": ".analysis_tmp/live_smoke/live_smoke_input_updated.xlsx",
        "expected_run_report": ".analysis_tmp/live_smoke/live_smoke_input_run_report.json",
        "errors": [],
        "warnings": [],
    }


def ok_repeatability():
    return {
        "status": "ok",
        "accepted": True,
        "run_count": 3,
        "min_runs": 3,
        "fixture_csv": "tests/fixtures/ocr_crops/ground_truth.csv",
        "settings": {
            "gpu": False,
            "detail": 0,
            "upscale_factor": 2.0,
            "upscale_method": "LANCZOS",
            "allowlist_mode": "none",
        },
        "errors": [],
        "warnings": [],
    }


def test_check_evidence_bundle_accepts_real_artifacts_with_live_comparison():
    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        live_comparison_report=ok_live_comparison(),
        live_smoke_report=ok_live_smoke(),
        repeatability_report=ok_repeatability(),
        require_live_comparison=True,
        require_live_smoke=True,
        require_repeatability=True,
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


def test_check_evidence_bundle_treats_required_live_gate_as_promotion_mode():
    matrix = ok_matrix()
    matrix["comparisons"][0]["against_baseline"]["accuracy_not_regressed"] = False

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=matrix,
        live_comparison_report=ok_live_comparison(),
        live_smoke_report=ok_live_smoke(),
        repeatability_report=ok_repeatability(),
        require_live_comparison=True,
        require_live_smoke=True,
        require_repeatability=True,
    )

    assert report["accepted"] is False
    assert report["strict_matrix_regressions"] is True
    assert any("failed accuracy_not_regressed" in error for error in report["errors"])


def test_check_evidence_bundle_allows_matrix_p95_regression_when_live_speed_passes():
    matrix = ok_matrix()
    matrix["comparisons"][0]["against_baseline"]["p95_latency_not_increased"] = False
    matrix["comparisons"][0]["against_baseline"]["field_comparisons"]["rate"][
        "p95_latency_not_increased"
    ] = False

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=matrix,
        live_comparison_report=ok_live_comparison(),
        live_smoke_report=ok_live_smoke(),
        repeatability_report=ok_repeatability(),
        require_live_comparison=True,
        require_live_smoke=True,
        require_repeatability=True,
    )

    assert report["accepted"] is True
    assert report["errors"] == []
    assert any("failed p95_latency_not_increased" in warning for warning in report["warnings"])


def test_check_evidence_bundle_explicit_no_matrix_regressions_rejects_p95_regression():
    matrix = ok_matrix()
    matrix["comparisons"][0]["against_baseline"]["p95_latency_not_increased"] = False

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=matrix,
        require_no_matrix_regressions=True,
    )

    assert report["accepted"] is False
    assert any("failed p95_latency_not_increased" in error for error in report["errors"])


def test_check_evidence_bundle_requires_live_comparison_when_requested():
    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        require_live_comparison=True,
    )

    assert report["accepted"] is False
    assert "live comparison is required but missing" in report["errors"]


def test_check_evidence_bundle_requires_live_smoke_when_requested():
    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        require_live_smoke=True,
    )

    assert report["accepted"] is False
    assert "live smoke is required but missing" in report["errors"]


def test_check_evidence_bundle_rejects_failed_live_smoke_report():
    failed_smoke = {
        **ok_live_smoke(),
        "status": "not_ready",
        "accepted": False,
        "errors": ["expected_output_workbook missing"],
    }

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        live_smoke_report=failed_smoke,
        require_live_smoke=True,
    )

    assert report["accepted"] is False
    assert "live smoke is not accepted" in report["errors"]
    assert "live smoke contains errors: expected_output_workbook missing" in report["errors"]


def test_check_evidence_bundle_requires_repeatability_when_requested():
    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        require_repeatability=True,
    )

    assert report["accepted"] is False
    assert "repeatability is required but missing" in report["errors"]


def test_check_evidence_bundle_rejects_failed_repeatability_report():
    failed_repeatability = {
        **ok_repeatability(),
        "status": "not_ready",
        "accepted": False,
        "errors": ["run 2 exact_accuracy changed: 0.99 != 1.0"],
    }

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        repeatability_report=failed_repeatability,
        require_repeatability=True,
    )

    assert report["accepted"] is False
    assert "repeatability is not accepted" in report["errors"]
    assert (
        "repeatability contains errors: run 2 exact_accuracy changed: 0.99 != 1.0"
        in report["errors"]
    )


def test_check_evidence_bundle_rejects_repeatability_fixture_mismatch():
    repeatability = {
        **ok_repeatability(),
        "fixture_csv": "tests/fixtures/other/ground_truth.csv",
    }

    report = check_evidence_bundle(
        audit_report=ready_audit(),
        benchmark_report=ok_benchmark(),
        matrix_report=ok_matrix(),
        repeatability_report=repeatability,
    )

    assert report["accepted"] is False
    assert "repeatability fixture_csv does not match fixture audit" in report["errors"]


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
    live_smoke_path = tmp_path / "live_smoke.json"
    repeatability_path = tmp_path / "repeatability.json"
    output_path = tmp_path / "bundle.json"
    audit_path.write_text(json.dumps(ready_audit()), encoding="utf-8")
    benchmark_path.write_text(json.dumps(ok_benchmark()), encoding="utf-8")
    matrix_path.write_text(json.dumps({**ok_matrix(), "dry_run": True}), encoding="utf-8")
    live_smoke_path.write_text(json.dumps(ok_live_smoke()), encoding="utf-8")
    repeatability_path.write_text(json.dumps(ok_repeatability()), encoding="utf-8")

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
            "--live-smoke-json",
            str(live_smoke_path),
            "--require-live-smoke",
            "--repeatability-json",
            str(repeatability_path),
            "--require-repeatability",
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
