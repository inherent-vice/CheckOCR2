"""Prepare OCR crop fixture drafts from saved date/rate detail images."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checkocr2.ocr_text import clean_date_text, clean_rate_text  # noqa: E402
from checkocr2.paths import sanitize_filename  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("tests/fixtures/ocr_crops")
DEFAULT_CSV_NAME = "ground_truth_draft.csv"
CANONICAL_GROUND_TRUTH_NAME = "ground_truth.csv"
SUPPORTED_SUFFIXES = {"_date": "date", "_rate": "rate"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Folder containing saved *_date.png/*_rate.png crops.",
    )
    parser.add_argument(
        "--run-report",
        type=Path,
        help="Optional run report used only for draft expected values.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--csv-name", default=DEFAULT_CSV_NAME)
    parser.add_argument("--source-run", help="Value to write in the source_run column.")
    parser.add_argument(
        "--fill-expected-from-report",
        action="store_true",
        help="Prefill expected_text from the run report. These values still require manual verification.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing fixture CSV or copied crops.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned fixture rows without writing files.",
    )
    parser.add_argument(
        "--allow-unsafe-output",
        action="store_true",
        help="Allow output outside ignored fixture, analysis, or temp folders.",
    )
    return parser.parse_args(argv)


def prepare_fixtures(
    *,
    source_dir: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    csv_name: str = DEFAULT_CSV_NAME,
    run_report: Path | None = None,
    source_run: str | None = None,
    fill_expected_from_report: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
    allow_unsafe_output: bool = False,
) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    validate_output_target(
        source_dir=source_dir,
        output_dir=output_dir,
        csv_name=csv_name,
        allow_unsafe_output=allow_unsafe_output,
    )
    csv_path = output_dir / csv_name

    if fill_expected_from_report and run_report is None:
        raise ValueError("--fill-expected-from-report requires --run-report")
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(f"source directory not found: {source_dir}")
    if csv_path.exists() and not overwrite and not dry_run:
        raise FileExistsError(f"fixture CSV already exists: {csv_path}")

    report_rows = (
        load_report_rows(run_report) if run_report and fill_expected_from_report else {}
    )
    source_run_value = source_run or infer_source_run(source_dir, run_report)
    crop_files = discover_crop_files(source_dir)
    if not crop_files:
        raise ValueError(f"no *_date.png or *_rate.png crops found under: {source_dir}")

    rows: list[dict[str, str]] = []
    planned_copies: list[tuple[Path, Path]] = []
    existing_outputs: list[str] = []
    for index, source_path in enumerate(crop_files, start=1):
        field = field_from_path(source_path)
        code_key = code_key_from_path(source_path)
        expected = ""
        notes = [
            f"source={display_relative(source_dir, source_path)}",
            "review_required",
        ]
        if fill_expected_from_report:
            expected = normalize(field, report_rows.get(code_key, {}).get(field, ""))
            notes.append("expected_from_run_report")
        output_name = fixture_filename(index, source_path, field)
        destination = output_dir / output_name
        if destination.exists() and not overwrite and not dry_run:
            existing_outputs.append(str(destination))
        planned_copies.append((source_path, destination))
        rows.append(
            {
                "crop_path": output_name,
                "field": field,
                "expected_text": expected,
                "source_run": source_run_value,
                "notes": "; ".join(notes),
            }
        )

    if existing_outputs:
        raise FileExistsError(
            "fixture crop already exists: " + ", ".join(existing_outputs[:3])
        )

    summary = {
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "fixture_csv": str(csv_path),
        "total_cases": len(rows),
        "field_counts": count_fields(rows),
        "filled_expected_count": sum(1 for row in rows if row["expected_text"]),
        "dry_run": dry_run,
        "rows": rows,
    }

    if dry_run:
        return summary

    output_dir.mkdir(parents=True, exist_ok=True)
    for source_path, destination in planned_copies:
        shutil.copy2(source_path, destination)
    write_fixture_csv(csv_path, rows)
    return summary


def discover_crop_files(source_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in source_dir.rglob("*.png")
        if path.is_file() and field_from_path(path) in {"date", "rate"}
    )


def field_from_path(path: Path) -> str:
    stem = path.stem.lower()
    for suffix, field in SUPPORTED_SUFFIXES.items():
        if stem.endswith(suffix):
            return field
    return ""


def code_key_from_path(path: Path) -> str:
    stem = path.stem
    for suffix in SUPPORTED_SUFFIXES:
        if stem.lower().endswith(suffix):
            return stem[: -len(suffix)].lower()
    return stem.lower()


def fixture_filename(index: int, source_path: Path, field: str) -> str:
    source_stem = crop_stem_without_field(source_path)
    safe_stem = sanitize_filename(source_stem)
    return f"{index:04d}_{safe_stem}_{field}.png"


def crop_stem_without_field(path: Path) -> str:
    stem = path.stem
    lower_stem = stem.lower()
    for suffix in SUPPORTED_SUFFIXES:
        if lower_stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def load_report_rows(run_report: Path) -> dict[str, dict[str, str]]:
    data = json.loads(run_report.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, str]] = {}
    for row in data.get("rows", []):
        code = str(row.get("code", "") or "").lower()
        if not code or code in rows:
            continue
        rows[code] = {
            "date": str(row.get("date", "") or ""),
            "rate": str(row.get("rate", "") or ""),
        }
    return rows


def normalize(field: str, text: str) -> str:
    if field.lower() == "date":
        return clean_date_text(text)
    if field.lower() == "rate":
        return clean_rate_text(text)
    return text.strip()


def validate_output_target(
    *,
    source_dir: Path,
    output_dir: Path,
    csv_name: str,
    allow_unsafe_output: bool = False,
) -> None:
    csv_path = Path(csv_name)
    if (
        csv_path.is_absolute()
        or csv_path.name != csv_name
        or csv_path.parent != Path(".")
    ):
        raise ValueError(f"csv_name must be a filename, not a path: {csv_name}")
    if csv_path.suffix.lower() != ".csv":
        raise ValueError(f"csv_name must end with .csv: {csv_name}")
    if csv_path.name.lower() == CANONICAL_GROUND_TRUTH_NAME:
        raise ValueError(
            "ground_truth.csv is reserved for manually reviewed fixtures; "
            "prepare_ocr_fixtures writes draft CSVs only"
        )

    if output_dir == source_dir or is_relative_to(output_dir, source_dir):
        raise ValueError(
            "output_dir must not be the source screenshot directory or one of its children"
        )

    root = ROOT.resolve()
    allowed_roots = [
        (root / "tests" / "fixtures" / "ocr_crops").resolve(),
        (root / ".analysis_tmp").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    if any(
        output_dir == allowed or is_relative_to(output_dir, allowed)
        for allowed in allowed_roots
    ):
        return
    if not allow_unsafe_output:
        raise ValueError(
            "output_dir must be under tests/fixtures/ocr_crops, .analysis_tmp, or the system temp directory; "
            "pass --allow-unsafe-output only for deliberate local experiments"
        )


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def write_fixture_csv(csv_path: Path, rows: list[dict[str, str]]) -> None:
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["crop_path", "field", "expected_text", "source_run", "notes"]
        )
        writer.writeheader()
        writer.writerows(rows)


def infer_source_run(source_dir: Path, run_report: Path | None) -> str:
    if run_report:
        return run_report.stem
    return source_dir.name


def display_relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def count_fields(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        field = row["field"]
        counts[field] = counts.get(field, 0) + 1
    return dict(sorted(counts.items()))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = prepare_fixtures(
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            csv_name=args.csv_name,
            run_report=args.run_report,
            source_run=args.source_run,
            fill_expected_from_report=args.fill_expected_from_report,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            allow_unsafe_output=args.allow_unsafe_output,
        )
    except (
        FileExistsError,
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
