"""Validate repeated OCR benchmark reports before candidate promotion."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_ocr import validate_output_path  # noqa: E402
from scripts.check_ocr_evidence_bundle import check_benchmark_report  # noqa: E402

DEFAULT_MIN_RUNS = 3
STABLE_TOP_LEVEL_METRICS = (
    "total_cases",
    "evaluated_cases",
    "missing_cases",
    "invalid_path_cases",
    "exact_accuracy",
    "blank_on_expected_nonempty_count",
    "false_positive_count",
)
STABLE_FIELD_METRICS = (
    "total_cases",
    "evaluated_cases",
    "missing_cases",
    "invalid_path_cases",
    "exact_accuracy",
    "blank_on_expected_nonempty_count",
    "false_positive_count",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-json", type=Path, nargs="+", required=True)
    parser.add_argument("--min-runs", type=positive_int, default=DEFAULT_MIN_RUNS)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--allow-repo-output", action="store_true")
    return parser.parse_args(argv)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"repeatability input must be a JSON object: {path}")
    return data


def check_ocr_repeatability(
    reports: list[dict[str, Any]],
    *,
    min_runs: int = DEFAULT_MIN_RUNS,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if len(reports) < min_runs:
        errors.append(
            f"repeatability requires at least {min_runs} runs: {len(reports)} provided"
        )

    for index, report in enumerate(reports, start=1):
        check = check_benchmark_report(report, f"repeat run {index}")
        errors.extend(check["errors"])
        warnings.extend(check["warnings"])

    if reports:
        compare_reports_to_first(reports, errors)

    accepted = not errors
    first = reports[0] if reports else {}
    return {
        "accepted": accepted,
        "status": "ok" if accepted else "not_ready",
        "run_count": len(reports),
        "min_runs": min_runs,
        "fixture_csv": str(first.get("fixture_csv", "") or ""),
        "settings": first.get("settings") if isinstance(first.get("settings"), dict) else {},
        "latency_summary": latency_summary(reports),
        "errors": errors,
        "warnings": warnings,
    }


def compare_reports_to_first(reports: list[dict[str, Any]], errors: list[str]) -> None:
    first = reports[0]
    first_fixture = normalized(first.get("fixture_csv"))
    first_settings = first.get("settings") if isinstance(first.get("settings"), dict) else {}
    first_fields = field_summaries(first)

    for index, report in enumerate(reports[1:], start=2):
        if normalized(report.get("fixture_csv")) != first_fixture:
            errors.append(f"run {index} fixture_csv does not match run 1")
        settings = report.get("settings") if isinstance(report.get("settings"), dict) else {}
        if settings != first_settings:
            errors.append(f"run {index} settings do not match run 1")
        compare_metrics(
            report,
            first,
            STABLE_TOP_LEVEL_METRICS,
            f"run {index}",
            errors,
        )
        compare_field_summaries(index, field_summaries(report), first_fields, errors)


def field_summaries(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    summaries = report.get("field_summaries")
    if not isinstance(summaries, dict):
        return {}
    return {
        str(field): summary
        for field, summary in summaries.items()
        if isinstance(summary, dict)
    }


def compare_field_summaries(
    run_index: int,
    summaries: dict[str, dict[str, Any]],
    first_summaries: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    if set(summaries) != set(first_summaries):
        errors.append(
            f"run {run_index} field_summaries fields changed: "
            f"{sorted(summaries)} != {sorted(first_summaries)}"
        )
    for field, first_summary in sorted(first_summaries.items()):
        summary = summaries.get(field)
        if summary is None:
            continue
        compare_metrics(
            summary,
            first_summary,
            STABLE_FIELD_METRICS,
            f"run {run_index} field {field}",
            errors,
        )


def compare_metrics(
    report: dict[str, Any],
    first: dict[str, Any],
    keys: tuple[str, ...],
    label: str,
    errors: list[str],
) -> None:
    for key in keys:
        current = report.get(key)
        expected = first.get(key)
        if current != expected:
            errors.append(f"{label} {key} changed: {current} != {expected}")


def latency_summary(reports: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    p95_values = [
        float(report["p95_latency_ms"])
        for report in reports
        if isinstance(report.get("p95_latency_ms"), int | float)
    ]
    return {"p95_latency_ms": numeric_summary(p95_values)}


def numeric_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(statistics.fmean(values), 3),
    }


def normalized(value: object) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


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
        reports = [load_json(path) for path in args.benchmark_json]
        report = check_ocr_repeatability(reports, min_runs=args.min_runs)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_or_print_report(report, args.output_json)
    return 0 if report["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
