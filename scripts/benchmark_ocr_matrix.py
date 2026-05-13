"""Run OCR benchmark combinations and summarize baseline regressions."""

from __future__ import annotations

import argparse
import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checkocr2.exceptions import OCREngineError  # noqa: E402
from checkocr2.ocr_engine import normalize_ocr_engine  # noqa: E402
from scripts.benchmark_ocr import run_benchmark, validate_output_path  # noqa: E402

DEFAULT_ENGINES = "easyocr"
DEFAULT_FACTORS = "1.0,1.5,2.0,2.5,3.0"
DEFAULT_METHODS = "BILINEAR,BICUBIC,LANCZOS"
DEFAULT_DETAILS = "0,1"
DEFAULT_ALLOWLIST_MODES = "none"


def parse_csv_floats(value: str) -> list[float]:
    parsed = [float(part.strip()) for part in value.split(",") if part.strip()]
    if not parsed:
        raise argparse.ArgumentTypeError("at least one float is required")
    return parsed


def parse_csv_ints(value: str) -> list[int]:
    parsed = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not parsed:
        raise argparse.ArgumentTypeError("at least one int is required")
    invalid = [item for item in parsed if item not in {0, 1}]
    if invalid:
        raise argparse.ArgumentTypeError("details must be 0 or 1")
    return parsed


def parse_csv_strings(value: str) -> list[str]:
    parsed = [part.strip().upper() for part in value.split(",") if part.strip()]
    if not parsed:
        raise argparse.ArgumentTypeError("at least one value is required")
    return parsed


def parse_csv_allowlist_modes(value: str) -> list[str]:
    parsed = [part.lower() for part in parse_csv_strings(value)]
    invalid = [mode for mode in parsed if mode not in {"none", "field"}]
    if invalid:
        raise argparse.ArgumentTypeError("allowlist modes must be none or field")
    return parsed


def parse_csv_engines(value: str) -> list[str]:
    try:
        parsed = [normalize_ocr_engine(part) for part in value.split(",") if part.strip()]
    except OCREngineError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not parsed:
        raise argparse.ArgumentTypeError("at least one engine is required")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-csv", type=Path, default=Path("tests/fixtures/ocr_crops/ground_truth.csv"))
    parser.add_argument("--output-json", type=Path, default=Path(".analysis_tmp/ocr_benchmark_matrix.json"))
    parser.add_argument("--allow-repo-output", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-empty-fixture", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--engines", type=parse_csv_engines, default=parse_csv_engines(DEFAULT_ENGINES))
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--upscale-factors", type=parse_csv_floats, default=parse_csv_floats(DEFAULT_FACTORS))
    parser.add_argument("--upscale-methods", type=parse_csv_strings, default=parse_csv_strings(DEFAULT_METHODS))
    parser.add_argument("--details", type=parse_csv_ints, default=parse_csv_ints(DEFAULT_DETAILS))
    parser.add_argument(
        "--allowlist-modes",
        type=parse_csv_allowlist_modes,
        default=parse_csv_allowlist_modes(DEFAULT_ALLOWLIST_MODES),
    )
    return parser.parse_args(argv)


def candidate_key(report: dict[str, Any]) -> str:
    settings = report.get("settings", {})
    engine_part = f"engine={settings.get('engine')};" if settings.get("engine") else ""
    return (
        engine_part
        + f"detail={settings.get('detail')};"
        f"factor={settings.get('upscale_factor')};"
        f"method={settings.get('upscale_method')};"
        f"allowlist={settings.get('allowlist_mode')}"
    )


def summarize_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": candidate_key(report),
        "status": report.get("status"),
        "settings": report.get("settings", {}),
        "total_cases": report.get("total_cases", 0),
        "evaluated_cases": report.get("evaluated_cases", 0),
        "missing_cases": report.get("missing_cases", 0),
        "invalid_path_cases": report.get("invalid_path_cases", 0),
        "exact_accuracy": report.get("exact_accuracy"),
        "blank_count": report.get("blank_count"),
        "blank_on_expected_nonempty_count": report.get("blank_on_expected_nonempty_count"),
        "false_positive_count": report.get("false_positive_count"),
        "p95_latency_ms": report.get("p95_latency_ms"),
        "field_summaries": report.get("field_summaries", {}),
    }


def candidate_blank_error_count(summary: dict[str, Any]) -> int:
    value = summary.get("blank_on_expected_nonempty_count")
    return summary.get("blank_count", 0) if value is None else value


def compare_field_summaries(
    candidate_fields: dict[str, dict[str, Any]],
    baseline_fields: dict[str, dict[str, Any]],
) -> dict[str, dict[str, bool | None]]:
    comparisons: dict[str, dict[str, bool | None]] = {}
    for field in sorted(set(candidate_fields) | set(baseline_fields)):
        candidate = candidate_fields.get(field)
        baseline = baseline_fields.get(field)
        if not candidate or not baseline:
            comparisons[field] = {
                "coverage_unchanged": None,
                "accuracy_not_regressed": None,
                "blank_not_increased": None,
                "false_positive_not_increased": None,
                "p95_latency_not_increased": None,
            }
            continue
        coverage_unchanged = (
            candidate.get("evaluated_cases") == baseline.get("evaluated_cases")
            and candidate.get("missing_cases", 0) == baseline.get("missing_cases", 0)
            and candidate.get("invalid_path_cases", 0) == baseline.get("invalid_path_cases", 0)
        )
        if not coverage_unchanged or not candidate.get("evaluated_cases"):
            comparisons[field] = {
                "coverage_unchanged": coverage_unchanged,
                "accuracy_not_regressed": None,
                "blank_not_increased": None,
                "false_positive_not_increased": None,
                "p95_latency_not_increased": None,
            }
            continue
        comparisons[field] = {
            "coverage_unchanged": True,
            "accuracy_not_regressed": candidate["exact_accuracy"] >= baseline["exact_accuracy"],
            "blank_not_increased": candidate_blank_error_count(candidate) <= candidate_blank_error_count(baseline),
            "false_positive_not_increased": candidate["false_positive_count"] <= baseline["false_positive_count"],
            "p95_latency_not_increased": candidate["p95_latency_ms"] <= baseline["p95_latency_ms"],
        }
    return comparisons


def compare_to_baseline(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    if candidate.get("status") != "ok" or baseline.get("status") != "ok":
        return {
            "accuracy_not_regressed": None,
            "blank_not_increased": None,
            "false_positive_not_increased": None,
            "p95_latency_not_increased": None,
            "coverage_unchanged": None,
            "field_comparisons": None,
        }
    coverage_unchanged = (
        candidate.get("evaluated_cases") == baseline.get("evaluated_cases")
        and candidate.get("missing_cases", 0) == baseline.get("missing_cases", 0)
        and candidate.get("invalid_path_cases", 0) == baseline.get("invalid_path_cases", 0)
    )
    field_comparisons = compare_field_summaries(
        candidate.get("field_summaries", {}),
        baseline.get("field_summaries", {}),
    )
    if not coverage_unchanged or not candidate.get("evaluated_cases"):
        return {
            "coverage_unchanged": coverage_unchanged,
            "accuracy_not_regressed": None,
            "blank_not_increased": None,
            "false_positive_not_increased": None,
            "p95_latency_not_increased": None,
            "field_comparisons": field_comparisons,
        }
    return {
        "coverage_unchanged": coverage_unchanged,
        "accuracy_not_regressed": candidate["exact_accuracy"] >= baseline["exact_accuracy"],
        "blank_not_increased": candidate_blank_error_count(candidate) <= candidate_blank_error_count(baseline),
        "false_positive_not_increased": candidate["false_positive_count"] <= baseline["false_positive_count"],
        "p95_latency_not_increased": candidate["p95_latency_ms"] <= baseline["p95_latency_ms"],
        "field_comparisons": field_comparisons,
    }


def benchmark_args(
    base_args: argparse.Namespace,
    *,
    factor: float,
    method: str,
    detail: int,
    allowlist_mode: str,
    engine: str,
) -> Namespace:
    return Namespace(
        fixture_csv=base_args.fixture_csv,
        limit=base_args.limit,
        allow_empty_fixture=base_args.allow_empty_fixture,
        dry_run=base_args.dry_run,
        engine=engine,
        gpu=base_args.gpu,
        detail=detail,
        upscale_factor=factor,
        upscale_method=method,
        allowlist_mode=allowlist_mode,
    )


def run_matrix(args: argparse.Namespace) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    baseline_summary: dict[str, Any] | None = None

    for engine in getattr(args, "engines", parse_csv_engines(DEFAULT_ENGINES)):
        for detail in args.details:
            for factor in args.upscale_factors:
                for method in args.upscale_methods:
                    for allowlist_mode in args.allowlist_modes:
                        report = run_benchmark(
                            benchmark_args(
                                args,
                                factor=factor,
                                method=method,
                                detail=detail,
                                allowlist_mode=allowlist_mode,
                                engine=engine,
                            )
                        )
                        summary = summarize_report(report)
                        reports.append(report)
                        summaries.append(summary)
                        if baseline_summary is None:
                            baseline_summary = summary

    baseline_summary = baseline_summary or {}
    comparisons = [
        {
            "key": summary["key"],
            "against_baseline": compare_to_baseline(summary, baseline_summary),
        }
        for summary in summaries
    ]
    return {
        "fixture_csv": str(args.fixture_csv),
        "dry_run": args.dry_run,
        "total_candidates": len(summaries),
        "baseline": baseline_summary,
        "candidates": summaries,
        "comparisons": comparisons,
        "reports": reports,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_output_path(args.output_json, args.allow_repo_output)
        report = run_matrix(args)
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"status": "ok", "output_json": str(args.output_json)}, ensure_ascii=False))
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
