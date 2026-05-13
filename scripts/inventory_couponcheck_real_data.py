"""Inventory real CouponCheck workbooks and saved OCR images."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_ocr import validate_output_path  # noqa: E402

DAY_PATTERN = re.compile(r"^List_CouponCheck_\((\d{8})\)$")
WORKBOOK_PATTERN = "List_CouponCheck_({day}).xlsx"
UPDATED_WORKBOOK_PATTERN = "List_CouponCheck_({day})_updated.xlsx"
DEFAULT_LIMIT = 20


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--allow-repo-output", action="store_true")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument(
        "--sample-images",
        type=int,
        default=25,
        help="Number of PNG files per day to inspect for image-size distribution.",
    )
    return parser.parse_args(argv)


def inventory_real_data(
    source: Path,
    *,
    limit: int = DEFAULT_LIMIT,
    sample_images: int = 25,
) -> dict[str, Any]:
    source = source.resolve()
    if not source.exists() or not source.is_dir():
        raise FileNotFoundError(f"source directory not found: {source}")
    if limit < 0:
        raise ValueError("limit must be zero or greater")
    if sample_images < 0:
        raise ValueError("sample-images must be zero or greater")

    day_dirs = discover_day_dirs(source)
    selected = day_dirs if limit == 0 else day_dirs[:limit]
    days = [inspect_day(source, day, day_dir, sample_images) for day, day_dir in selected]
    return {
        "status": "ok",
        "source": str(source),
        "limit": limit,
        "sample_images": sample_images,
        "total_day_dirs": len(day_dirs),
        "inventoried_day_count": len(days),
        "days": days,
        "summary": summarize_days(days),
    }


def discover_day_dirs(source: Path) -> list[tuple[str, Path]]:
    days: list[tuple[str, Path]] = []
    for child in source.iterdir():
        if not child.is_dir():
            continue
        match = DAY_PATTERN.match(child.name)
        if match:
            days.append((match.group(1), child))
    return sorted(days, key=lambda item: item[0], reverse=True)


def inspect_day(
    source: Path,
    day: str,
    day_dir: Path,
    sample_images: int,
) -> dict[str, Any]:
    workbook = source / WORKBOOK_PATTERN.format(day=day)
    updated_workbook = source / UPDATED_WORKBOOK_PATTERN.format(day=day)
    png_files = sorted(path for path in day_dir.iterdir() if is_png_file(path))
    date_crops = [path for path in png_files if path.stem.lower().endswith("_date")]
    rate_crops = [path for path in png_files if path.stem.lower().endswith("_rate")]
    full_area = [
        path
        for path in png_files
        if path not in set(date_crops)
        and path not in set(rate_crops)
    ]
    return {
        "day": day,
        "folder": str(day_dir),
        "workbook": file_summary(workbook),
        "updated_workbook": file_summary(updated_workbook),
        "png_count": len(png_files),
        "full_area_png_count": len(full_area),
        "date_crop_count": len(date_crops),
        "rate_crop_count": len(rate_crops),
        "image_size_counts": image_size_counts(png_files[:sample_images]),
        "sample_png_names": [path.name for path in png_files[: min(10, len(png_files))]],
        "missing_inputs": missing_inputs(workbook, updated_workbook, png_files),
    }


def is_png_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".png"


def file_summary(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"path": str(path), "exists": False}
    stat = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "last_write_time": stat.st_mtime,
    }


def image_size_counts(paths: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in paths:
        try:
            with Image.open(path) as image:
                key = f"{image.width}x{image.height}"
        except (OSError, UnidentifiedImageError):
            key = "unreadable"
        counts[key] = counts.get(key, 0) + 1
    return counts


def missing_inputs(workbook: Path, updated_workbook: Path, png_files: list[Path]) -> list[str]:
    missing = []
    if not workbook.exists():
        missing.append("workbook")
    if not updated_workbook.exists():
        missing.append("updated_workbook")
    if not png_files:
        missing.append("png_folder_empty")
    return missing


def summarize_days(days: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "png_count_total": sum(day["png_count"] for day in days),
        "date_crop_count_total": sum(day["date_crop_count"] for day in days),
        "rate_crop_count_total": sum(day["rate_crop_count"] for day in days),
        "days_with_missing_inputs": [
            day["day"] for day in days if day["missing_inputs"]
        ],
        "image_size_counts": aggregate_image_sizes(days),
    }


def aggregate_image_sizes(days: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for day in days:
        for size, count in day["image_size_counts"].items():
            counts[size] = counts.get(size, 0) + int(count)
    return counts


def write_or_print(payload: dict[str, Any], output_json: Path | None) -> None:
    output = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if output_json is None:
        print(output)
        return
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(output + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_output_path(args.output_json, args.allow_repo_output)
        payload = inventory_real_data(
            args.source,
            limit=args.limit,
            sample_images=args.sample_images,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_or_print(payload, args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

