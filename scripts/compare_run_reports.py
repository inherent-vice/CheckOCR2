"""Compare two CheckOCR2 live OCR run reports for same-input regressions."""

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

from checkocr2.models import STATUS_DONE  # noqa: E402
from scripts.benchmark_ocr import p95, validate_output_path  # noqa: E402

DEFAULT_MIN_ROWS = 10
SUCCESS_STATUSES = {STATUS_DONE, "done", "complete", "completed"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_report", type=Path)
    parser.add_argument("candidate_report", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--allow-repo-output", action="store_true")
    parser.add_argument("--min-rows", type=int, default=DEFAULT_MIN_ROWS)
    parser.add_argument(
        "--allow-output-changes",
        action="store_true",
        help="Do not fail when date/rate outputs differ; use only for manual review runs",
    )
    parser.add_argument(
        "--allow-different-input",
        action="store_true",
        help="Skip row identity checks; not recommended for wait/default tuning",
    )
    return parser.parse_args(argv)


def load_json_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_reports(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    min_rows: int = DEFAULT_MIN_ROWS,
    allow_output_changes: bool = False,
    require_same_input: bool = True,
) -> dict[str, Any]:
    baseline_rows = list(baseline.get("rows", []))
    candidate_rows = list(candidate.get("rows", []))
    errors: list[str] = []
    timing_errors: list[str] = []
    output_changes = find_output_changes(baseline_rows, candidate_rows)

    same_input = True
    if min(len(baseline_rows), len(candidate_rows)) < min_rows:
        same_input = False
        errors.append(
            "minimum row count not met: "
            f"baseline={len(baseline_rows)}, candidate={len(candidate_rows)}, required={min_rows}"
        )
    if require_same_input:
        same_input = validate_same_input_paths(baseline, candidate, errors) and same_input
        same_input = validate_same_input_rows(baseline_rows, candidate_rows, errors) and same_input

    baseline_metrics = summarize_report(baseline, "baseline", timing_errors)
    candidate_metrics = summarize_report(candidate, "candidate", timing_errors)
    errors.extend(timing_errors)
    blank_not_increased = candidate_metrics["blank_total"] <= baseline_metrics["blank_total"]
    failure_not_increased = candidate_metrics["failure_count"] <= baseline_metrics["failure_count"]
    outputs_unchanged = not output_changes

    gates = {
        "same_input": same_input,
        "outputs_unchanged": outputs_unchanged or allow_output_changes,
        "blank_not_increased": blank_not_increased,
        "failure_not_increased": failure_not_increased,
        "timing_values_valid": not timing_errors,
    }
    accepted = all(gates.values())

    baseline_p95 = baseline_metrics["p95_row_total_ms"]
    candidate_p95 = candidate_metrics["p95_row_total_ms"]
    timing = {
        "baseline_p95_row_total_ms": baseline_p95,
        "candidate_p95_row_total_ms": candidate_p95,
        "p95_row_total_improved": (
            candidate_p95 < baseline_p95 if baseline_p95 is not None and candidate_p95 is not None else None
        ),
    }

    return {
        "status": "ok" if accepted else "regression",
        "accepted": accepted,
        "min_rows": min_rows,
        "baseline_input_excel_path": baseline.get("input_excel_path"),
        "candidate_input_excel_path": candidate.get("input_excel_path"),
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "gates": gates,
        "timing": timing,
        "output_changes": output_changes,
        "errors": errors,
    }


def validate_same_input_paths(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    errors: list[str],
) -> bool:
    baseline_path = str(baseline.get("input_excel_path", "") or "")
    candidate_path = str(candidate.get("input_excel_path", "") or "")
    if normalize_report_path(baseline_path) == normalize_report_path(candidate_path):
        return True
    errors.append(f"input Excel path mismatch: {baseline_path} != {candidate_path}")
    return False


def normalize_report_path(path_value: str) -> str:
    return os.path.normcase(os.path.normpath(path_value.strip()))


def validate_same_input_rows(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    errors: list[str],
) -> bool:
    same_input = True
    if len(baseline_rows) != len(candidate_rows):
        errors.append(f"row count mismatch: baseline={len(baseline_rows)}, candidate={len(candidate_rows)}")
        same_input = False

    for index, (baseline_row, candidate_row) in enumerate(zip(baseline_rows, candidate_rows, strict=False)):
        baseline_key = row_identity(baseline_row)
        candidate_key = row_identity(candidate_row)
        if baseline_key != candidate_key:
            errors.append(
                f"row identity mismatch at index {index}: "
                f"{baseline_key[0]}/{baseline_key[1]} != {candidate_key[0]}/{candidate_key[1]}"
            )
            same_input = False
    return same_input


def row_identity(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("code", "") or ""), str(row.get("name", "") or "")


def find_output_changes(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for index, (baseline_row, candidate_row) in enumerate(zip(baseline_rows, candidate_rows, strict=False)):
        for field in ("date", "rate"):
            baseline_value = str(baseline_row.get(field, "") or "")
            candidate_value = str(candidate_row.get(field, "") or "")
            if baseline_value != candidate_value:
                changes.append(
                    {
                        "index": index,
                        "code": str(baseline_row.get("code", "") or ""),
                        "field": field,
                        "baseline": baseline_value,
                        "candidate": candidate_value,
                    }
                )
    return changes


def summarize_report(
    report: dict[str, Any],
    label: str,
    timing_errors: list[str],
) -> dict[str, Any]:
    rows = list(report.get("rows", []))
    row_total_values: list[float] = []
    for position, row in enumerate(rows):
        timing = row.get("timing_ms")
        if not isinstance(timing, dict) or timing.get("row_total_ms") is None:
            continue
        raw_value = timing["row_total_ms"]
        try:
            row_total_values.append(float(raw_value))
        except (TypeError, ValueError):
            row_index = row.get("index", position)
            timing_errors.append(f"{label} row {row_index} has non-numeric row_total_ms: {raw_value}")
    blank_date_count = sum(1 for row in rows if not str(row.get("date", "") or "").strip())
    blank_rate_count = sum(1 for row in rows if not str(row.get("rate", "") or "").strip())
    failure_count = sum(1 for row in rows if is_failure_row(row))
    return {
        "total_rows": len(rows),
        "processed_count": report.get("summary", {}).get("processed_count"),
        "blank_date_count": blank_date_count,
        "blank_rate_count": blank_rate_count,
        "blank_total": blank_date_count + blank_rate_count,
        "failure_count": failure_count,
        "p95_row_total_ms": round(p95(row_total_values), 3) if row_total_values else None,
    }


def is_failure_row(row: dict[str, Any]) -> bool:
    failure_reason = str(row.get("failure_reason", "") or "").strip()
    if failure_reason:
        return True
    if "failure_reason" in row:
        return False
    status = str(row.get("status", "") or "").strip()
    return bool(status and status not in SUCCESS_STATUSES)


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
        baseline = load_json_report(args.baseline_report)
        candidate = load_json_report(args.candidate_report)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = compare_reports(
        baseline,
        candidate,
        min_rows=args.min_rows,
        allow_output_changes=args.allow_output_changes,
        require_same_input=not args.allow_different_input,
    )
    write_or_print_report(report, args.output_json)
    return 0 if report["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
