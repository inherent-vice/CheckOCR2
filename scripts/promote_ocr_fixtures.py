"""Promote manually reviewed OCR fixture drafts to ground truth."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_ocr_fixtures import (  # noqa: E402
    DEFAULT_MIN_DATE,
    DEFAULT_MIN_RATE,
    DEFAULT_MIN_TOTAL,
    DRAFT_NOTE_MARKERS,
    audit_fixtures,
)
from scripts.prepare_ocr_fixtures import (  # noqa: E402
    CANONICAL_GROUND_TRUTH_NAME,
    DEFAULT_CSV_NAME,
    DEFAULT_OUTPUT_DIR,
)

DEFAULT_DRAFT_CSV = DEFAULT_OUTPUT_DIR / DEFAULT_CSV_NAME
DEFAULT_OUTPUT_CSV = DEFAULT_OUTPUT_DIR / CANONICAL_GROUND_TRUTH_NAME
FIELDNAMES = ["crop_path", "field", "expected_text", "source_run", "notes"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-csv", type=Path, default=DEFAULT_DRAFT_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument(
        "--confirm-reviewed",
        action="store_true",
        help="Required acknowledgement that every expected_text value was manually checked.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing ground truth CSV after validation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the promotion summary without writing ground_truth.csv.",
    )
    parser.add_argument("--min-total", type=int, default=DEFAULT_MIN_TOTAL)
    parser.add_argument("--min-date", type=int, default=DEFAULT_MIN_DATE)
    parser.add_argument("--min-rate", type=int, default=DEFAULT_MIN_RATE)
    return parser.parse_args(argv)


def promote_fixtures(
    *,
    draft_csv: Path,
    output_csv: Path | None = None,
    reviewed_by: str,
    confirm_reviewed: bool,
    overwrite: bool = False,
    dry_run: bool = False,
    min_total: int = DEFAULT_MIN_TOTAL,
    min_by_field: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Validate a reviewed draft and write the canonical ground truth CSV."""

    if not confirm_reviewed:
        raise ValueError("--confirm-reviewed is required after manual crop review")
    reviewer = reviewed_by.strip()
    if not reviewer:
        raise ValueError("reviewed_by is required")

    draft_csv = draft_csv.resolve()
    output_csv = (output_csv or draft_csv.with_name(CANONICAL_GROUND_TRUTH_NAME)).resolve()
    validate_output_csv(draft_csv, output_csv)
    if output_csv.exists() and not overwrite and not dry_run:
        raise FileExistsError(f"ground truth CSV already exists: {output_csv}")

    rows = read_fixture_rows(draft_csv)
    promoted_rows = promoted_fixture_rows(rows, reviewer)
    validate_reviewed_rows(promoted_rows)

    audit_path = draft_csv
    if not dry_run:
        audit_path = output_csv.with_name(f".{output_csv.name}.promotion_tmp")
        write_fixture_csv(audit_path, promoted_rows)

    minimums = {"date": DEFAULT_MIN_DATE, "rate": DEFAULT_MIN_RATE}
    if min_by_field is not None:
        minimums.update(min_by_field)
    try:
        report = audit_fixtures(
            audit_path,
            min_total=min_total,
            min_by_field=minimums,
        )
        if not report["ready_for_baseline"]:
            raise ValueError(
                "promoted fixture audit failed: " + "; ".join(report["errors"])
            )
        if not dry_run:
            audit_path.replace(output_csv)
    finally:
        if audit_path != draft_csv and audit_path.exists():
            audit_path.unlink()

    return {
        "status": report["status"],
        "ready_for_baseline": report["ready_for_baseline"],
        "draft_csv": str(draft_csv),
        "output_csv": str(output_csv),
        "reviewed_by": reviewer,
        "total_cases": report["total_cases"],
        "field_counts": report["field_counts"],
        "dry_run": dry_run,
    }


def read_fixture_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"draft CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {field: str(row.get(field, "") or "") for field in FIELDNAMES}
            for row in reader
        ]


def validate_output_csv(draft_csv: Path, output_csv: Path) -> None:
    if output_csv.name != CANONICAL_GROUND_TRUTH_NAME:
        raise ValueError(f"output_csv must be named {CANONICAL_GROUND_TRUTH_NAME}")
    if output_csv.parent != draft_csv.parent:
        raise ValueError("output_csv must be in the same directory as draft_csv")


def promoted_fixture_rows(
    rows: list[dict[str, str]],
    reviewed_by: str,
) -> list[dict[str, str]]:
    promoted = []
    for row in rows:
        promoted_row = {field: str(row.get(field, "") or "") for field in FIELDNAMES}
        promoted_row["notes"] = append_reviewer_note(promoted_row["notes"], reviewed_by)
        promoted.append(promoted_row)
    return promoted


def append_reviewer_note(notes: str, reviewed_by: str) -> str:
    note_parts = [part.strip() for part in notes.split(";") if part.strip()]
    reviewer_note = f"reviewed_by={reviewed_by}"
    if reviewer_note not in note_parts:
        note_parts.append(reviewer_note)
    return "; ".join(note_parts)


def validate_reviewed_rows(rows: list[dict[str, str]]) -> None:
    errors: list[str] = []
    if not rows:
        errors.append("draft CSV has no rows")
    for row in rows:
        crop_path = row.get("crop_path", "")
        expected_text = row.get("expected_text", "")
        if not expected_text:
            errors.append(f"blank expected_text for {crop_path}")
        notes = row.get("notes", "").lower()
        for marker in DRAFT_NOTE_MARKERS:
            if marker in notes:
                errors.append(f"draft marker remains for {crop_path}: {marker}")
    if errors:
        raise ValueError("; ".join(errors))


def write_fixture_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = promote_fixtures(
            draft_csv=args.draft_csv,
            output_csv=args.output_csv,
            reviewed_by=args.reviewed_by,
            confirm_reviewed=args.confirm_reviewed,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            min_total=args.min_total,
            min_by_field={"date": args.min_date, "rate": args.min_rate},
        )
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
