"""Prepare an ignored workbook workspace for a small live OCR smoke run."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checkocr2.excel_io import export_grid_rows, load_grid_rows  # noqa: E402
from checkocr2.models import CODE_COL, NAME_COL  # noqa: E402
from checkocr2.paths import updated_workbook_path  # noqa: E402
from checkocr2.run_report import report_output_path  # noqa: E402

DEFAULT_OUTPUT_DIR = Path(".analysis_tmp/live_smoke")
DEFAULT_INPUT_NAME = "live_smoke_input.xlsx"
DEFAULT_MANIFEST_NAME = "live_smoke_manifest.json"
DEFAULT_ROW_COUNT = 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-excel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--input-name", default=DEFAULT_INPUT_NAME)
    parser.add_argument("--manifest-name", default=DEFAULT_MANIFEST_NAME)
    parser.add_argument("--rows", type=positive_int, default=DEFAULT_ROW_COUNT)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing smoke input workbook or manifest.",
    )
    parser.add_argument(
        "--allow-unsafe-output",
        action="store_true",
        help="Allow output outside .analysis_tmp or the system temp directory.",
    )
    return parser.parse_args(argv)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def prepare_live_smoke_workspace(
    *,
    source_excel: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    input_name: str = DEFAULT_INPUT_NAME,
    manifest_name: str = DEFAULT_MANIFEST_NAME,
    rows: int = DEFAULT_ROW_COUNT,
    overwrite: bool = False,
    allow_unsafe_output: bool = False,
) -> dict[str, Any]:
    """Create a small copied-input workspace for a real live OCR smoke."""

    if rows <= 0:
        raise ValueError("rows must be greater than zero")
    source_excel = source_excel.resolve()
    output_dir = output_dir.resolve()
    validate_workspace_target(
        output_dir=output_dir,
        input_name=input_name,
        manifest_name=manifest_name,
        allow_unsafe_output=allow_unsafe_output,
    )
    if not source_excel.exists() or not source_excel.is_file():
        raise FileNotFoundError(f"source Excel not found: {source_excel}")

    smoke_input_path = output_dir / input_name
    manifest_path = output_dir / manifest_name
    existing_outputs = [
        str(path)
        for path in (smoke_input_path, manifest_path)
        if path.exists() and not overwrite
    ]
    if existing_outputs:
        raise FileExistsError("live smoke output already exists: " + ", ".join(existing_outputs))

    loaded_rows, missing_columns = load_grid_rows(source_excel)
    smoke_rows = first_smoke_rows(loaded_rows, rows)
    if not smoke_rows:
        raise ValueError("source Excel has no rows with a nonblank item code")

    output_dir.mkdir(parents=True, exist_ok=True)
    export_grid_rows(smoke_rows, smoke_input_path)

    expected_output_workbook = updated_workbook_path(output_dir, str(smoke_input_path))
    expected_run_report = report_output_path(output_dir, str(smoke_input_path))
    manifest = {
        "status": "ready",
        "source_excel": str(source_excel),
        "source_sha256": sha256_file(source_excel),
        "source_size_bytes": source_excel.stat().st_size,
        "smoke_input": str(smoke_input_path),
        "smoke_input_sha256": sha256_file(smoke_input_path),
        "output_dir": str(output_dir),
        "expected_output_workbook": str(expected_output_workbook),
        "expected_run_report": str(expected_run_report),
        "row_count": len(smoke_rows),
        "requested_rows": rows,
        "missing_columns": missing_columns,
        "rows": [
            {
                "code": row.get(CODE_COL, ""),
                "name": row.get(NAME_COL, ""),
            }
            for row in smoke_rows
        ],
        "instructions": [
            "Open CheckOCR2 with this smoke_input workbook.",
            "Use output_dir as the output folder.",
            "After a 1-2 row live run, verify expected_output_workbook and expected_run_report exist.",
            "Compare source_sha256 with the source file if production-mutation risk is suspected.",
        ],
    }
    write_json_atomic(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def validate_workspace_target(
    *,
    output_dir: Path,
    input_name: str,
    manifest_name: str,
    allow_unsafe_output: bool = False,
) -> None:
    validate_filename(input_name, ".xlsx", "input_name")
    validate_filename(manifest_name, ".json", "manifest_name")
    root = ROOT.resolve()
    allowed_roots = [
        (root / ".analysis_tmp").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    if any(output_dir == allowed or is_relative_to(output_dir, allowed) for allowed in allowed_roots):
        return
    if not allow_unsafe_output:
        raise ValueError(
            "output_dir must be under .analysis_tmp or the system temp directory; "
            "pass --allow-unsafe-output only for deliberate local experiments"
        )


def validate_filename(value: str, suffix: str, label: str) -> None:
    path = Path(value)
    if path.is_absolute() or path.name != value or path.parent != Path("."):
        raise ValueError(f"{label} must be a filename, not a path: {value}")
    if path.suffix.lower() != suffix:
        raise ValueError(f"{label} must end with {suffix}: {value}")


def first_smoke_rows(rows: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    selected = []
    for row in rows:
        if not str(row.get(CODE_COL, "") or "").strip():
            continue
        selected.append(row)
        if len(selected) >= count:
            break
    return selected


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = prepare_live_smoke_workspace(
            source_excel=args.source_excel,
            output_dir=args.output_dir,
            input_name=args.input_name,
            manifest_name=args.manifest_name,
            rows=args.rows,
            overwrite=args.overwrite,
            allow_unsafe_output=args.allow_unsafe_output,
        )
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
