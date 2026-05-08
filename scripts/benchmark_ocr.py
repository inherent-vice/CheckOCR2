"""Benchmark OCR crops against a normalized ground-truth CSV."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIELD_ALLOWLISTS = {
    "date": "0123456789./-",
    "rate": "0123456789.,%",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-csv", type=Path, default=Path("tests/fixtures/ocr_crops/ground_truth.csv"))
    parser.add_argument("--output-json", type=Path)
    parser.add_argument(
        "--allow-repo-output",
        action="store_true",
        help="Allow writing benchmark reports inside the repository outside .analysis_tmp",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate fixture metadata without loading OCR")
    parser.add_argument(
        "--allow-empty-fixture",
        action="store_true",
        help="Allow a missing or empty fixture CSV while bootstrapping benchmark data",
    )
    parser.add_argument("--limit", type=int, default=0)
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


def load_cases(fixture_csv: Path, limit: int = 0, *, allow_empty: bool = False) -> list[dict[str, str]]:
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
            raise ValueError(f"Fixture CSV missing columns: {', '.join(missing_columns)}")
        rows = list(reader)
    if not rows and not allow_empty:
        raise ValueError(f"Fixture CSV has no cases: {fixture_csv}")
    return rows[:limit] if limit > 0 else rows


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
        raise ValueError("Write benchmark reports under .analysis_tmp/ or pass --allow-repo-output")


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


def extract_text(results: list[Any], detail: int) -> tuple[str, float | None]:
    if detail == 0:
        return " ".join(str(item) for item in results).strip(), None

    texts: list[str] = []
    confidences: list[float] = []
    for item in results:
        if isinstance(item, list | tuple) and len(item) >= 3:
            texts.append(str(item[1]))
            try:
                confidences.append(float(item[2]))
            except (TypeError, ValueError):
                pass
    confidence = statistics.fmean(confidences) if confidences else None
    return " ".join(texts).strip(), confidence


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=20, method="inclusive")[18]


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    cases = load_cases(args.fixture_csv, args.limit, allow_empty=args.allow_empty_fixture)
    allowlist_mode = getattr(args, "allowlist_mode", "none")
    report: dict[str, Any] = {
        "fixture_csv": str(args.fixture_csv),
        "total_cases": len(cases),
        "settings": {
            "gpu": args.gpu,
            "detail": args.detail,
            "upscale_factor": args.upscale_factor,
            "upscale_method": args.upscale_method,
            "allowlist_mode": allowlist_mode,
        },
        "dry_run": args.dry_run,
        "results": [],
    }

    if args.dry_run or not cases:
        report["status"] = "dry_run" if args.dry_run else "no_cases"
        return report

    import easyocr
    import numpy as np
    from PIL import Image

    from checkocr2.image_processing import upscale_image

    reader = easyocr.Reader(["en"], gpu=args.gpu)
    fixture_dir = args.fixture_csv.parent
    latencies_ms: list[float] = []
    exact = blank = false_positive = missing = invalid_path = 0

    for case in cases:
        field = case.get("field", "")
        expected = normalize(field, case.get("expected_text", ""))
        crop_path_value = case.get("crop_path", "")
        try:
            crop_path = resolve_crop_path(fixture_dir, crop_path_value)
        except ValueError as exc:
            invalid_path += 1
            report["results"].append({"crop_path": crop_path_value, "status": "invalid_path", "error": str(exc)})
            continue
        if not crop_path.exists():
            missing += 1
            report["results"].append({"crop_path": str(crop_path), "status": "missing"})
            continue

        start = time.perf_counter()
        image = Image.open(crop_path).convert("RGB")
        image = upscale_image(
            image,
            enabled=args.upscale_factor > 1.0,
            factor=args.upscale_factor,
            method=args.upscale_method,
        )
        allowlist = allowlist_for_field(field, allowlist_mode)
        readtext_kwargs: dict[str, Any] = {"detail": args.detail}
        if allowlist is not None:
            readtext_kwargs["allowlist"] = allowlist
        raw_results = reader.readtext(np.array(image), **readtext_kwargs)
        latency = (time.perf_counter() - start) * 1000
        latencies_ms.append(latency)

        raw_text, confidence = extract_text(raw_results, args.detail)
        normalized = normalize(field, raw_text)
        matched = normalized == expected
        exact += int(matched)
        blank += int(not normalized)
        false_positive += int(not expected and bool(normalized))
        report["results"].append(
            {
                "crop_path": str(crop_path),
                "field": field,
                "expected": expected,
                "raw_text": raw_text,
                "normalized": normalized,
                "confidence": confidence,
                "allowlist": allowlist,
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
            "false_positive_count": false_positive,
            "p95_latency_ms": round(p95(latencies_ms), 2),
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
