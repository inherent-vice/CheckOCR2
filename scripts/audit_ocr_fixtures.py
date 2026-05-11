"""Audit OCR crop fixtures before running accuracy benchmarks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_ocr import (  # noqa: E402
    load_cases,
    normalize,
    resolve_crop_path,
    validate_output_path,
)

DEFAULT_FIXTURE_CSV = Path("tests/fixtures/ocr_crops/ground_truth.csv")
DEFAULT_MIN_TOTAL = 100
DEFAULT_MIN_DATE = 50
DEFAULT_MIN_RATE = 50
SUPPORTED_FIELDS = {"date", "rate"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-csv", type=Path, default=DEFAULT_FIXTURE_CSV)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--allow-repo-output", action="store_true")
    parser.add_argument("--min-total", type=int, default=DEFAULT_MIN_TOTAL)
    parser.add_argument("--min-date", type=int, default=DEFAULT_MIN_DATE)
    parser.add_argument("--min-rate", type=int, default=DEFAULT_MIN_RATE)
    return parser.parse_args(argv)


def audit_fixtures(
    fixture_csv: Path,
    *,
    min_total: int = DEFAULT_MIN_TOTAL,
    min_by_field: dict[str, int] | None = None,
) -> dict[str, Any]:
    minimums = {"date": DEFAULT_MIN_DATE, "rate": DEFAULT_MIN_RATE}
    if min_by_field is not None:
        minimums.update(min_by_field)

    report: dict[str, Any] = {
        "fixture_csv": str(fixture_csv),
        "minimums": {"total": min_total, **minimums},
        "total_cases": 0,
        "field_counts": {},
        "duplicate_crop_paths": [],
        "blank_expected_cases": 0,
        "image_size": {},
        "errors": [],
    }

    try:
        cases = load_cases(fixture_csv, allow_empty=False)
    except (FileNotFoundError, ValueError) as exc:
        report["errors"].append(str(exc))
        return finalize_report(report)

    fixture_dir = fixture_csv.parent
    seen_crop_paths: set[str] = set()
    seen_crop_files: set[str] = set()
    widths: list[int] = []
    heights: list[int] = []
    field_counts: dict[str, int] = {}

    for case in cases:
        crop_path_value = str(case.get("crop_path", "") or "")
        field = str(case.get("field", "") or "").lower()
        expected_text = str(case.get("expected_text", "") or "")
        report["total_cases"] += 1
        field_counts[field] = field_counts.get(field, 0) + 1

        if field not in SUPPORTED_FIELDS:
            report["errors"].append(f"unsupported field for {crop_path_value}: {field}")

        normalized_expected = normalize(field, expected_text)
        if expected_text and normalized_expected != expected_text:
            report["errors"].append(
                f"expected_text is not normalized for {crop_path_value}: "
                f"{expected_text} -> {normalized_expected}"
            )
        if not expected_text:
            report["blank_expected_cases"] += 1

        try:
            crop_path = resolve_crop_path(fixture_dir, crop_path_value)
        except ValueError as exc:
            report["errors"].append(str(exc))
            continue

        if crop_path_value in seen_crop_paths:
            report["duplicate_crop_paths"].append(crop_path_value)
            report["errors"].append(f"duplicate crop_path: {crop_path_value}")
        seen_crop_paths.add(crop_path_value)

        crop_file_key = normalized_file_key(crop_path)
        if crop_file_key in seen_crop_files:
            report["duplicate_crop_paths"].append(crop_path_value)
            report["errors"].append(
                f"duplicate crop file: {crop_path_value} resolves to {display_path(fixture_dir, crop_path)}"
            )
        seen_crop_files.add(crop_file_key)

        if not crop_path.exists():
            report["errors"].append(f"missing crop file: {crop_path_value}")
            continue

        try:
            with Image.open(crop_path) as image:
                width, height = image.size
        except (OSError, UnidentifiedImageError) as exc:
            report["errors"].append(f"unreadable crop file: {crop_path_value}: {exc}")
            continue
        widths.append(width)
        heights.append(height)

    report["field_counts"] = {field: field_counts[field] for field in sorted(field_counts)}
    if widths and heights:
        report["image_size"] = {
            "min_width": min(widths),
            "max_width": max(widths),
            "min_height": min(heights),
            "max_height": max(heights),
        }

    if report["total_cases"] < min_total:
        report["errors"].append(f"minimum total cases not met: {report['total_cases']} < {min_total}")
    for field, minimum in minimums.items():
        count = field_counts.get(field, 0)
        if count < minimum:
            report["errors"].append(f"minimum {field} cases not met: {count} < {minimum}")

    return finalize_report(report)


def finalize_report(report: dict[str, Any]) -> dict[str, Any]:
    report["ready_for_baseline"] = not report["errors"]
    report["status"] = "ready" if report["ready_for_baseline"] else "not_ready"
    return report


def normalized_file_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def display_path(fixture_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(fixture_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


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
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = audit_fixtures(
        args.fixture_csv,
        min_total=args.min_total,
        min_by_field={"date": args.min_date, "rate": args.min_rate},
    )
    write_or_print_report(report, args.output_json)
    return 0 if report["ready_for_baseline"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
