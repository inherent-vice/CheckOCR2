"""Validate that OCR evidence artifacts are real enough for tuning decisions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_ocr import validate_output_path  # noqa: E402

DEFAULT_AUDIT_JSON = Path(".analysis_tmp/ocr_fixture_audit.json")
DEFAULT_BENCHMARK_JSON = Path(".analysis_tmp/easyocr_baseline.json")
DEFAULT_MATRIX_JSON = Path(".analysis_tmp/ocr_benchmark_matrix_allowlist.json")

MATRIX_REGRESSION_FLAGS = (
    "coverage_unchanged",
    "accuracy_not_regressed",
    "blank_not_increased",
    "false_positive_not_increased",
    "p95_latency_not_increased",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT_JSON)
    parser.add_argument("--benchmark-json", type=Path, default=DEFAULT_BENCHMARK_JSON)
    parser.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX_JSON)
    parser.add_argument("--live-comparison-json", type=Path)
    parser.add_argument("--live-smoke-json", type=Path)
    parser.add_argument("--repeatability-json", type=Path)
    parser.add_argument(
        "--require-live-comparison",
        action="store_true",
        help="Fail unless --live-comparison-json is provided and accepted.",
    )
    parser.add_argument(
        "--require-live-smoke",
        action="store_true",
        help="Fail unless --live-smoke-json is provided and accepted.",
    )
    parser.add_argument(
        "--require-repeatability",
        action="store_true",
        help="Fail unless --repeatability-json is provided and accepted.",
    )
    parser.add_argument(
        "--require-no-matrix-regressions",
        action="store_true",
        help="Fail on any matrix accuracy, blank, false-positive, or P95 regression.",
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--allow-repo-output", action="store_true")
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_evidence_bundle(
    *,
    audit_report: dict[str, Any],
    benchmark_report: dict[str, Any],
    matrix_report: dict[str, Any],
    live_comparison_report: dict[str, Any] | None = None,
    live_smoke_report: dict[str, Any] | None = None,
    repeatability_report: dict[str, Any] | None = None,
    require_live_comparison: bool = False,
    require_live_smoke: bool = False,
    require_repeatability: bool = False,
    require_no_matrix_regressions: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    strict_matrix_regressions = (
        require_no_matrix_regressions
        or require_live_comparison
        or require_live_smoke
        or require_repeatability
    )
    checks = {
        "fixture_audit": check_fixture_audit(audit_report),
        "benchmark": check_benchmark_report(benchmark_report, "benchmark"),
        "matrix": check_matrix_report(
            matrix_report,
            require_no_regressions=strict_matrix_regressions,
        ),
        "artifact_consistency": check_artifact_consistency(
            audit_report,
            benchmark_report,
            matrix_report,
            repeatability_report,
        ),
        "live_comparison": check_live_comparison_report(
            live_comparison_report,
            required=require_live_comparison,
        ),
        "live_smoke": check_live_smoke_report(
            live_smoke_report,
            required=require_live_smoke,
        ),
        "repeatability": check_repeatability_report(
            repeatability_report,
            required=require_repeatability,
        ),
    }

    for check in checks.values():
        errors.extend(check["errors"])
        warnings.extend(check["warnings"])

    accepted = not errors
    return {
        "status": "ready" if accepted else "not_ready",
        "accepted": accepted,
        "strict_matrix_regressions": strict_matrix_regressions,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def base_check(name: str) -> dict[str, Any]:
    return {"name": name, "accepted": True, "errors": [], "warnings": []}


def reject(check: dict[str, Any], message: str) -> None:
    check["accepted"] = False
    check["errors"].append(message)


def warn(check: dict[str, Any], message: str) -> None:
    check["warnings"].append(message)


def check_fixture_audit(report: dict[str, Any]) -> dict[str, Any]:
    check = base_check("fixture_audit")
    if report.get("status") != "ready" or report.get("ready_for_baseline") is not True:
        reject(check, "fixture audit is not ready")
    if report.get("errors"):
        reject(check, "fixture audit contains errors")
    require_positive_int(check, report, "total_cases", "fixture audit")
    field_counts = report.get("field_counts")
    if not isinstance(field_counts, dict) or not field_counts:
        reject(check, "fixture audit has no field_counts")
    return check


def check_benchmark_report(report: dict[str, Any], label: str) -> dict[str, Any]:
    check = base_check(label)
    if report.get("dry_run") is True:
        reject(check, f"{label} is a dry-run artifact")
    if report.get("status") != "ok":
        reject(check, f"{label} status is not ok: {report.get('status')}")
    require_positive_int(check, report, "total_cases", label)
    require_positive_int(check, report, "evaluated_cases", label)
    require_zero_int(check, report, "missing_cases", label)
    require_zero_int(check, report, "invalid_path_cases", label)
    if report.get("exact_accuracy") is None:
        reject(check, f"{label} exact_accuracy is missing")
    field_summaries = report.get("field_summaries")
    if not isinstance(field_summaries, dict) or not field_summaries:
        reject(check, f"{label} has no field_summaries")
    return check


def check_matrix_report(
    report: dict[str, Any],
    *,
    require_no_regressions: bool = False,
) -> dict[str, Any]:
    check = base_check("matrix")
    if report.get("dry_run") is True:
        reject(check, "matrix is a dry-run artifact")
    require_positive_int(check, report, "total_candidates", "matrix")
    if report.get("dry_run") is True:
        return check

    baseline = report.get("baseline")
    if not isinstance(baseline, dict):
        reject(check, "matrix baseline is missing")
    else:
        merge_child_errors(check, check_benchmark_report(baseline, "matrix baseline"))

    candidates = report.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        reject(check, "matrix has no candidates")
    else:
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                reject(check, f"matrix candidate {index} is not an object")
                continue
            merge_child_errors(
                check,
                check_benchmark_report(candidate, f"matrix candidate {index}"),
            )

    comparisons = report.get("comparisons")
    if not isinstance(comparisons, list) or not comparisons:
        reject(check, "matrix has no comparisons")
    else:
        for index, comparison in enumerate(comparisons):
            check_matrix_comparison(
                check,
                comparison,
                index,
                require_no_regressions=require_no_regressions,
            )
    return check


def check_matrix_comparison(
    check: dict[str, Any],
    comparison: Any,
    index: int,
    *,
    require_no_regressions: bool,
) -> None:
    if not isinstance(comparison, dict):
        reject(check, f"matrix comparison {index} is not an object")
        return
    against = comparison.get("against_baseline")
    key = comparison.get("key", f"index {index}")
    if not isinstance(against, dict):
        reject(check, f"matrix comparison {key} is missing against_baseline")
        return
    check_matrix_flags(
        check,
        against,
        f"matrix comparison {key}",
        require_no_regressions=require_no_regressions,
    )
    field_comparisons = against.get("field_comparisons")
    if not isinstance(field_comparisons, dict) or not field_comparisons:
        reject(check, f"matrix comparison {key} has no field_comparisons")
        return
    for field, field_result in field_comparisons.items():
        if not isinstance(field_result, dict):
            reject(check, f"matrix comparison {key} field {field} is not an object")
            continue
        check_matrix_flags(
            check,
            field_result,
            f"matrix comparison {key} field {field}",
            require_no_regressions=require_no_regressions,
        )


def check_matrix_flags(
    check: dict[str, Any],
    result: dict[str, Any],
    label: str,
    *,
    require_no_regressions: bool,
) -> None:
    if result.get("coverage_unchanged") is not True:
        reject(check, f"{label} failed coverage_unchanged")
    for flag in MATRIX_REGRESSION_FLAGS:
        if flag == "coverage_unchanged":
            continue
        if result.get(flag) is True:
            continue
        message = f"{label} failed {flag}"
        if require_no_regressions:
            reject(check, message)
        else:
            warn(check, message)


def check_live_comparison_report(
    report: dict[str, Any] | None,
    *,
    required: bool,
) -> dict[str, Any]:
    check = base_check("live_comparison")
    if report is None:
        if required:
            reject(check, "live comparison is required but missing")
        else:
            warn(check, "live comparison not provided")
        return check
    if report.get("accepted") is not True or report.get("status") != "ok":
        reject(check, "live comparison is not accepted")
    gates = report.get("gates")
    if not isinstance(gates, dict) or not gates:
        reject(check, "live comparison has no gates")
    else:
        for gate_name, value in sorted(gates.items()):
            if value is not True:
                reject(check, f"live comparison gate failed: {gate_name}")
    return check


def check_live_smoke_report(
    report: dict[str, Any] | None,
    *,
    required: bool,
) -> dict[str, Any]:
    check = base_check("live_smoke")
    if report is None:
        if required:
            reject(check, "live smoke is required but missing")
        else:
            warn(check, "live smoke not provided")
        return check
    if report.get("accepted") is not True or report.get("status") != "ok":
        reject(check, "live smoke is not accepted")
    report_errors = report.get("errors")
    if isinstance(report_errors, list) and report_errors:
        reject(check, "live smoke contains errors: " + "; ".join(map(str, report_errors)))
    for key in ("manifest", "smoke_input", "expected_output_workbook", "expected_run_report"):
        if not str(report.get(key, "") or ""):
            reject(check, f"live smoke report missing {key}")
    return check


def check_repeatability_report(
    report: dict[str, Any] | None,
    *,
    required: bool,
) -> dict[str, Any]:
    check = base_check("repeatability")
    if report is None:
        if required:
            reject(check, "repeatability is required but missing")
        else:
            warn(check, "repeatability not provided")
        return check
    if report.get("accepted") is not True or report.get("status") != "ok":
        reject(check, "repeatability is not accepted")
    report_errors = report.get("errors")
    if isinstance(report_errors, list) and report_errors:
        reject(check, "repeatability contains errors: " + "; ".join(map(str, report_errors)))
    if not isinstance(report.get("run_count"), int) or report.get("run_count") < 3:
        reject(check, "repeatability run_count must be at least 3")
    if not str(report.get("fixture_csv", "") or ""):
        reject(check, "repeatability fixture_csv is missing")
    return check


def check_artifact_consistency(
    audit_report: dict[str, Any],
    benchmark_report: dict[str, Any],
    matrix_report: dict[str, Any],
    repeatability_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    check = base_check("artifact_consistency")
    audit_fixture = normalized_report_path(audit_report.get("fixture_csv"))
    benchmark_fixture = normalized_report_path(benchmark_report.get("fixture_csv"))
    matrix_fixture = normalized_report_path(matrix_report.get("fixture_csv"))
    repeatability_fixture = (
        normalized_report_path(repeatability_report.get("fixture_csv"))
        if isinstance(repeatability_report, dict)
        else ""
    )
    if not audit_fixture:
        reject(check, "fixture audit fixture_csv is missing")
    if not benchmark_fixture:
        reject(check, "benchmark fixture_csv is missing")
    if not matrix_fixture:
        reject(check, "matrix fixture_csv is missing")
    if audit_fixture and benchmark_fixture and audit_fixture != benchmark_fixture:
        reject(check, "benchmark fixture_csv does not match fixture audit")
    if audit_fixture and matrix_fixture and audit_fixture != matrix_fixture:
        reject(check, "matrix fixture_csv does not match fixture audit")
    if audit_fixture and repeatability_fixture and audit_fixture != repeatability_fixture:
        reject(check, "repeatability fixture_csv does not match fixture audit")

    audit_total = audit_report.get("total_cases")
    if isinstance(audit_total, int) and audit_total > 0:
        require_matching_int(check, benchmark_report, "total_cases", audit_total, "benchmark")
        baseline = matrix_report.get("baseline")
        if isinstance(baseline, dict):
            require_matching_int(check, baseline, "total_cases", audit_total, "matrix baseline")
        for index, candidate in enumerate(matrix_report.get("candidates", [])):
            if isinstance(candidate, dict):
                require_matching_int(
                    check,
                    candidate,
                    "total_cases",
                    audit_total,
                    f"matrix candidate {index}",
                )

    audit_field_counts = audit_report.get("field_counts")
    if isinstance(audit_field_counts, dict) and audit_field_counts:
        check_field_coverage(
            check,
            benchmark_report.get("field_summaries"),
            audit_field_counts,
            "benchmark",
        )
        baseline = matrix_report.get("baseline")
        if isinstance(baseline, dict):
            check_field_coverage(
                check,
                baseline.get("field_summaries"),
                audit_field_counts,
                "matrix baseline",
            )
        for index, candidate in enumerate(matrix_report.get("candidates", [])):
            if isinstance(candidate, dict):
                check_field_coverage(
                    check,
                    candidate.get("field_summaries"),
                    audit_field_counts,
                    f"matrix candidate {index}",
                )
    return check


def normalized_report_path(value: Any) -> str:
    if not value:
        return ""
    return os.path.normcase(os.path.normpath(str(value).strip()))


def require_matching_int(
    check: dict[str, Any],
    report: dict[str, Any],
    key: str,
    expected: int,
    label: str,
) -> None:
    value = report.get(key)
    if value != expected:
        reject(check, f"{label} {key} does not match fixture audit: {value} != {expected}")


def check_field_coverage(
    check: dict[str, Any],
    field_summaries: Any,
    audit_field_counts: dict[str, Any],
    label: str,
) -> None:
    if not isinstance(field_summaries, dict) or not field_summaries:
        reject(check, f"{label} field_summaries are missing")
        return
    summary_fields = set(field_summaries)
    audit_fields = set(audit_field_counts)
    if summary_fields != audit_fields:
        reject(
            check,
            f"{label} field_summaries do not match fixture audit fields: "
            f"{sorted(summary_fields)} != {sorted(audit_fields)}",
        )
    for field, expected_count in audit_field_counts.items():
        summary = field_summaries.get(field)
        if not isinstance(summary, dict):
            reject(check, f"{label} field {field} summary is missing")
            continue
        if summary.get("total_cases") != expected_count:
            reject(
                check,
                f"{label} field {field} total_cases does not match fixture audit: "
                f"{summary.get('total_cases')} != {expected_count}",
            )
        if summary.get("evaluated_cases") != expected_count:
            reject(
                check,
                f"{label} field {field} evaluated_cases does not match fixture audit: "
                f"{summary.get('evaluated_cases')} != {expected_count}",
            )


def merge_child_errors(parent: dict[str, Any], child: dict[str, Any]) -> None:
    if not child["accepted"]:
        parent["accepted"] = False
    parent["errors"].extend(child["errors"])
    parent["warnings"].extend(child["warnings"])


def require_positive_int(
    check: dict[str, Any],
    report: dict[str, Any],
    key: str,
    label: str,
) -> None:
    value = report.get(key)
    if not isinstance(value, int) or value <= 0:
        reject(check, f"{label} {key} must be greater than zero")


def require_zero_int(
    check: dict[str, Any],
    report: dict[str, Any],
    key: str,
    label: str,
) -> None:
    value = report.get(key, 0)
    if not isinstance(value, int) or value != 0:
        reject(check, f"{label} {key} must be zero")


def write_or_print_report(report: dict[str, Any], output_json: Path | None) -> None:
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if output_json is None:
        print(output)
        return
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(output + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_output_path(args.output_json, args.allow_repo_output)
        report = check_evidence_bundle(
            audit_report=load_json(args.audit_json),
            benchmark_report=load_json(args.benchmark_json),
            matrix_report=load_json(args.matrix_json),
            live_comparison_report=(
                load_json(args.live_comparison_json)
                if args.live_comparison_json is not None
                else None
            ),
            live_smoke_report=(
                load_json(args.live_smoke_json)
                if args.live_smoke_json is not None
                else None
            ),
            repeatability_report=(
                load_json(args.repeatability_json)
                if args.repeatability_json is not None
                else None
            ),
            require_live_comparison=args.require_live_comparison,
            require_live_smoke=args.require_live_smoke,
            require_repeatability=args.require_repeatability,
            require_no_matrix_regressions=args.require_no_matrix_regressions,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    write_or_print_report(report, args.output_json)
    return 0 if report["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
