"""Benchmark OCR crops against a normalized ground-truth CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checkocr2.ocr_engine import (  # noqa: E402
    create_ocr_reader,
    default_ocr_languages,
    normalize_ocr_engine,
)
from checkocr2.ocr_field_extraction import (  # noqa: E402
    select_field_text_from_ocr_results,
)
from checkocr2.ocr_paddle_engine import (  # noqa: E402
    create_paddleocr_pipeline_reader,
)

FIELD_ALLOWLISTS = {
    "date": "0123456789./-",
    "rate": "0123456789.,%",
}
DRAFT_NOTE_MARKERS = ("review_required", "expected_from_run_report")
ROI_PROFILE_RE = re.compile(r"roi_profile=([a-z0-9_]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture-csv",
        type=Path,
        default=Path("tests/fixtures/ocr_crops/ground_truth.csv"),
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument(
        "--allow-repo-output",
        action="store_true",
        help="Allow writing benchmark reports inside the repository outside .analysis_tmp",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate fixture metadata without loading OCR",
    )
    parser.add_argument(
        "--allow-empty-fixture",
        action="store_true",
        help="Allow a missing or empty fixture CSV while bootstrapping benchmark data",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--engine",
        default="easyocr",
        type=normalize_ocr_engine,
        help="OCR engine to benchmark: easyocr or paddle.",
    )
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--detail", type=int, choices=(0, 1), default=0)
    parser.add_argument("--upscale-factor", type=float, default=2.0)
    parser.add_argument("--upscale-method", default="LANCZOS")
    parser.add_argument(
        "--allowlist-mode",
        choices=("none", "field"),
        default="none",
        help="Pass field-specific EasyOCR character allowlists for date/rate crops",
    )
    return parser.parse_args()


def load_cases(
    fixture_csv: Path, limit: int = 0, *, allow_empty: bool = False
) -> list[dict[str, str]]:
    if not fixture_csv.exists():
        if allow_empty:
            return []
        raise FileNotFoundError(f"Fixture CSV not found: {fixture_csv}")
    with fixture_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required_columns = {"crop_path", "field", "expected_text"}
        fieldnames = set(reader.fieldnames or [])
        missing_columns = sorted(required_columns - fieldnames)
        if missing_columns:
            raise ValueError(
                f"Fixture CSV missing columns: {', '.join(missing_columns)}"
            )
        rows = list(reader)
    if not rows and not allow_empty:
        raise ValueError(f"Fixture CSV has no cases: {fixture_csv}")
    return rows[:limit] if limit > 0 else rows


def validate_benchmark_cases(cases: list[dict[str, str]]) -> None:
    for case in cases:
        notes = str(case.get("notes", "") or "").lower()
        for marker in DRAFT_NOTE_MARKERS:
            if marker in notes:
                crop_path = case.get("crop_path", "")
                raise ValueError(
                    "Fixture CSV contains draft marker "
                    f"for {crop_path}: {marker}. Run the fixture audit and "
                    "promote a manually reviewed ground_truth.csv before benchmarking."
                )


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def resolve_crop_path(fixture_dir: Path, crop_path_value: str) -> Path:
    crop_path = Path(crop_path_value)
    if crop_path.is_absolute():
        raise ValueError(f"crop_path must be relative: {crop_path_value}")
    resolved = (fixture_dir / crop_path).resolve()
    fixture_root = fixture_dir.resolve()
    if not is_relative_to(resolved, fixture_root):
        raise ValueError(f"crop_path escapes fixture directory: {crop_path_value}")
    return resolved


def validate_output_path(output_json: Path | None, allow_repo_output: bool) -> None:
    if output_json is None or allow_repo_output:
        return
    resolved = output_json.resolve()
    root = ROOT.resolve()
    if not is_relative_to(resolved, root):
        return
    allowed_dir = (root / ".analysis_tmp").resolve()
    if not is_relative_to(resolved, allowed_dir):
        raise ValueError(
            "Write benchmark reports under .analysis_tmp/ or pass --allow-repo-output"
        )


def normalize(field: str, text: str) -> str:
    from checkocr2.ocr_text import clean_date_text, clean_rate_text

    if field.lower() == "date":
        return clean_date_text(text)
    if field.lower() == "rate":
        return clean_rate_text(text)
    return text.strip()


def allowlist_for_field(field: str, mode: str) -> str | None:
    if mode != "field":
        return None
    return FIELD_ALLOWLISTS.get(field.lower())


def roi_profile_from_notes(notes: str) -> str:
    match = ROI_PROFILE_RE.search(notes)
    if match:
        return match.group(1)
    return "cropped"


def resolve_source_image_path(
    case: dict[str, str],
    fixture_dir: Path,
) -> Path | None:
    source_image_path = str(case.get("source_image_path", "") or "").strip()
    if source_image_path:
        candidate = Path(source_image_path)
        if candidate.exists():
            return candidate
        if not candidate.is_absolute():
            resolved = (fixture_dir / candidate).resolve()
            if resolved.exists():
                return resolved

    notes = str(case.get("notes", "") or "")
    source_match = re.search(r"source=([^;]+)", notes)
    if not source_match:
        return None
    source_rel = source_match.group(1).strip()
    if not source_rel:
        return None

    for sibling in fixture_dir.parent.iterdir():
        if not sibling.is_dir() or not sibling.name.startswith("real_data"):
            continue
        candidate = (sibling / source_rel).resolve()
        if candidate.exists():
            return candidate
    return None


def extract_text(results: list[Any], detail: int) -> tuple[str, float | None]:
    from checkocr2.ocr_engine import extract_text_with_confidence

    return extract_text_with_confidence(results, detail)


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=20, method="inclusive")[18]


def empty_field_stats() -> dict[str, Any]:
    return {
        "total_cases": 0,
        "evaluated_cases": 0,
        "missing_cases": 0,
        "invalid_path_cases": 0,
        "exact_matches": 0,
        "blank_count": 0,
        "blank_on_expected_nonempty_count": 0,
        "false_positive_count": 0,
        "latencies_ms": [],
    }


def summarize_field_stats(
    field_stats: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for field, stats in sorted(field_stats.items()):
        evaluated = stats["evaluated_cases"]
        summaries[field] = {
            "total_cases": stats["total_cases"],
            "evaluated_cases": evaluated,
            "missing_cases": stats["missing_cases"],
            "invalid_path_cases": stats["invalid_path_cases"],
            "exact_accuracy": (
                (stats["exact_matches"] / evaluated) if evaluated else 0.0
            ),
            "blank_count": stats["blank_count"],
            "blank_on_expected_nonempty_count": stats[
                "blank_on_expected_nonempty_count"
            ],
            "false_positive_count": stats["false_positive_count"],
            "p95_latency_ms": round(p95(stats["latencies_ms"]), 2),
        }
    return summaries


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    cases = load_cases(
        args.fixture_csv, args.limit, allow_empty=args.allow_empty_fixture
    )
    validate_benchmark_cases(cases)
    allowlist_mode = getattr(args, "allowlist_mode", "none")
    report: dict[str, Any] = {
        "fixture_csv": str(args.fixture_csv),
        "total_cases": len(cases),
        "settings": {
            "engine": args.engine,
            "gpu": args.gpu,
            "detail": args.detail,
            "upscale_factor": args.upscale_factor,
            "upscale_method": args.upscale_method,
            "allowlist_mode": allowlist_mode,
        },
        "dry_run": args.dry_run,
        "results": [],
        "field_summaries": {},
    }

    if args.dry_run or not cases:
        report["status"] = "dry_run" if args.dry_run else "no_cases"
        return report

    import numpy as np
    from PIL import Image

    from checkocr2.image_processing import upscale_image

    reader = create_ocr_reader(args.engine, default_ocr_languages(args.engine), gpu=args.gpu)
    rate_reader = None
    fixture_dir = args.fixture_csv.parent
    latencies_ms: list[float] = []
    field_stats: dict[str, dict[str, Any]] = {}
    exact = blank = blank_on_expected_nonempty = false_positive = missing = (
        invalid_path
    ) = 0

    for case in cases:
        field = case.get("field", "")
        field_key = field.lower() or "unknown"
        stats = field_stats.setdefault(field_key, empty_field_stats())
        stats["total_cases"] += 1
        expected = normalize(field, case.get("expected_text", ""))
        crop_path_value = case.get("crop_path", "")
        roi_profile = roi_profile_from_notes(str(case.get("notes", "") or ""))
        try:
            crop_path = resolve_crop_path(fixture_dir, crop_path_value)
        except ValueError as exc:
            invalid_path += 1
            stats["invalid_path_cases"] += 1
            report["results"].append(
                {
                    "crop_path": crop_path_value,
                    "field": field,
                    "expected": expected,
                    "status": "invalid_path",
                    "error": str(exc),
                }
            )
            continue
        if not crop_path.exists():
            missing += 1
            stats["missing_cases"] += 1
            report["results"].append(
                {
                    "crop_path": str(crop_path),
                    "field": field,
                    "expected": expected,
                    "status": "missing",
                }
            )
            continue

        start = time.perf_counter()
        allowlist = allowlist_for_field(field, allowlist_mode)
        source_image_path = resolve_source_image_path(case, fixture_dir)
        if args.engine == "paddle" and field_key == "rate" and rate_reader is None:
            rate_reader = create_paddleocr_pipeline_reader(
                default_ocr_languages(args.engine),
                gpu=args.gpu,
            )
        active_reader = rate_reader if args.engine == "paddle" and field_key == "rate" and rate_reader is not None else reader
        image = Image.open(crop_path).convert("RGB")
        image = upscale_image(
            image,
            enabled=args.upscale_factor > 1.0,
            factor=args.upscale_factor,
            method=args.upscale_method,
        )
        raw_text = ""
        confidence: float | None = None
        readtext_kwargs = {"detail": args.detail}
        if allowlist is not None:
            readtext_kwargs["allowlist"] = allowlist
        raw_results = active_reader.readtext(np.array(image), **readtext_kwargs)
        if args.engine == "paddle" and field_key == "rate":
            raw_text = select_field_text_from_ocr_results(raw_results, field)
        else:
            raw_text, confidence = extract_text(raw_results, args.detail)
        latency = (time.perf_counter() - start) * 1000
        latencies_ms.append(latency)
        normalized = normalize(field, raw_text)
        matched = normalized == expected
        exact += int(matched)
        blank += int(not normalized)
        blank_on_expected_nonempty += int(bool(expected) and not normalized)
        false_positive += int(not expected and bool(normalized))
        stats["evaluated_cases"] += 1
        stats["exact_matches"] += int(matched)
        stats["blank_count"] += int(not normalized)
        stats["blank_on_expected_nonempty_count"] += int(
            bool(expected) and not normalized
        )
        stats["false_positive_count"] += int(not expected and bool(normalized))
        stats["latencies_ms"].append(latency)
        report["results"].append(
            {
                "crop_path": str(crop_path),
                "field": field,
                "expected": expected,
                "raw_text": raw_text,
                "normalized": normalized,
                "confidence": confidence,
                "allowlist": allowlist,
                "roi_profile": roi_profile,
                "ocr_source_path": str(source_image_path) if source_image_path else None,
                "latency_ms": round(latency, 2),
                "matched": matched,
            }
        )

    evaluated = len(cases) - missing - invalid_path
    report.update(
        {
            "status": "ok",
            "evaluated_cases": evaluated,
            "missing_cases": missing,
            "invalid_path_cases": invalid_path,
            "exact_accuracy": (exact / evaluated) if evaluated else 0.0,
            "blank_count": blank,
            "blank_on_expected_nonempty_count": blank_on_expected_nonempty,
            "false_positive_count": false_positive,
            "p95_latency_ms": round(p95(latencies_ms), 2),
            "field_summaries": summarize_field_stats(field_stats),
        }
    )
    return report


def main() -> int:
    args = parse_args()
    try:
        validate_output_path(args.output_json, args.allow_repo_output)
        report = run_benchmark(args)
        output = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output_json:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
