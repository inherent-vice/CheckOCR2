"""Verify artifacts from a small live OCR smoke workspace."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checkocr2.excel_io import load_grid_rows  # noqa: E402
from scripts.prepare_live_smoke_workspace import (  # noqa: E402
    DEFAULT_MANIFEST_NAME,
    DEFAULT_OUTPUT_DIR,
    sha256_file,
)

DEFAULT_MANIFEST_PATH = DEFAULT_OUTPUT_DIR / DEFAULT_MANIFEST_NAME
DEFAULT_MIN_PROCESSED = 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--allow-repo-output", action="store_true")
    parser.add_argument("--min-processed", type=positive_int, default=DEFAULT_MIN_PROCESSED)
    return parser.parse_args(argv)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def check_live_smoke_workspace(
    manifest_path: Path,
    *,
    min_processed: int = DEFAULT_MIN_PROCESSED,
) -> dict[str, Any]:
    """Check that a prepared live-smoke workspace has completed safely."""

    errors: list[str] = []
    warnings: list[str] = []
    manifest = load_json_file(manifest_path, errors, label="manifest")

    source_excel = manifest_path_from_value(manifest, "source_excel", errors)
    smoke_input = manifest_path_from_value(manifest, "smoke_input", errors)
    output_dir = manifest_path_from_value(manifest, "output_dir", errors)
    expected_output_workbook = manifest_path_from_value(
        manifest,
        "expected_output_workbook",
        errors,
    )
    expected_run_report = manifest_path_from_value(manifest, "expected_run_report", errors)

    check_workspace_paths(
        source_excel=source_excel,
        smoke_input=smoke_input,
        output_dir=output_dir,
        expected_output_workbook=expected_output_workbook,
        expected_run_report=expected_run_report,
        errors=errors,
    )

    check_file_hash(
        source_excel,
        manifest.get("source_sha256"),
        errors,
        label="source_excel",
    )
    check_file_hash(
        smoke_input,
        manifest.get("smoke_input_sha256"),
        errors,
        label="smoke_input",
    )
    check_existing_file(expected_output_workbook, errors, label="expected_output_workbook")
    check_existing_file(expected_run_report, errors, label="expected_run_report")

    report = load_json_file(expected_run_report, errors, label="expected_run_report")
    check_run_report(
        report,
        smoke_input=smoke_input,
        output_dir=output_dir,
        expected_output_workbook=expected_output_workbook,
        min_processed=min_processed,
        errors=errors,
    )
    check_output_workbook(
        expected_output_workbook,
        expected_rows=int_value(manifest.get("row_count")),
        errors=errors,
        warnings=warnings,
    )

    accepted = not errors
    return {
        "accepted": accepted,
        "status": "ok" if accepted else "not_ready",
        "manifest": str(manifest_path),
        "source_excel": str(source_excel) if source_excel else "",
        "smoke_input": str(smoke_input) if smoke_input else "",
        "output_dir": str(output_dir) if output_dir else "",
        "expected_output_workbook": (
            str(expected_output_workbook) if expected_output_workbook else ""
        ),
        "expected_run_report": str(expected_run_report) if expected_run_report else "",
        "min_processed": min_processed,
        "errors": errors,
        "warnings": warnings,
    }


def manifest_path_from_value(
    manifest: dict[str, Any],
    key: str,
    errors: list[str],
) -> Path | None:
    value = str(manifest.get(key, "") or "")
    if not value:
        errors.append(f"manifest missing {key}")
        return None
    return Path(value).resolve()


def check_file_hash(
    path: Path | None,
    expected_hash: object,
    errors: list[str],
    *,
    label: str,
) -> None:
    if path is None:
        return
    if not path.exists() or not path.is_file():
        errors.append(f"{label} missing: {path}")
        return
    expected = str(expected_hash or "")
    if not expected:
        errors.append(f"manifest missing {label}_sha256")
        return
    actual = sha256_file(path)
    if actual != expected:
        errors.append(f"{label} hash changed: {actual} != {expected}")


def check_existing_file(path: Path | None, errors: list[str], *, label: str) -> None:
    if path is None:
        return
    if not path.exists() or not path.is_file():
        errors.append(f"{label} missing: {path}")


def check_workspace_paths(
    *,
    source_excel: Path | None,
    smoke_input: Path | None,
    output_dir: Path | None,
    expected_output_workbook: Path | None,
    expected_run_report: Path | None,
    errors: list[str],
) -> None:
    if source_excel is not None and smoke_input is not None:
        if normalize_path(source_excel) == normalize_path(smoke_input):
            errors.append("smoke_input must not be the source_excel")
    if output_dir is None:
        return
    for label, path in (
        ("smoke_input", smoke_input),
        ("expected_output_workbook", expected_output_workbook),
        ("expected_run_report", expected_run_report),
    ):
        if path is not None and not is_relative_to(path, output_dir):
            errors.append(f"{label} must be under output_dir: {path} not under {output_dir}")


def check_run_report(
    report: dict[str, Any],
    *,
    smoke_input: Path | None,
    output_dir: Path | None,
    expected_output_workbook: Path | None,
    min_processed: int,
    errors: list[str],
) -> None:
    if not report:
        return
    if smoke_input is not None and normalize_path(report.get("input_excel_path")) != normalize_path(smoke_input):
        errors.append(
            "run report input_excel_path mismatch: "
            f"{report.get('input_excel_path')} != {smoke_input}"
        )
    if output_dir is not None and normalize_path(report.get("output_dir")) != normalize_path(output_dir):
        errors.append(f"run report output_dir mismatch: {report.get('output_dir')} != {output_dir}")

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("run report summary is missing")
        return
    processed_count = int_value(summary.get("processed_count"))
    if processed_count < min_processed:
        errors.append(
            f"run report processed_count too small: {processed_count} < {min_processed}"
        )
    if summary.get("stopped") is True:
        errors.append("run report indicates the smoke run was stopped")
    report_errors = list(report.get("errors", []))
    if report_errors:
        errors.append("run report contains errors: " + "; ".join(map(str, report_errors)))
    if expected_output_workbook is not None and normalize_path(
        summary.get("output_workbook_path")
    ) != normalize_path(expected_output_workbook):
        errors.append(
            "run report output_workbook_path mismatch: "
            f"{summary.get('output_workbook_path')} != {expected_output_workbook}"
        )
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) < min_processed:
        row_count = len(rows) if isinstance(rows, list) else 0
        errors.append(f"run report row count too small: {row_count} < {min_processed}")


def check_output_workbook(
    output_workbook: Path | None,
    *,
    expected_rows: int,
    errors: list[str],
    warnings: list[str],
) -> None:
    if output_workbook is None or not output_workbook.exists():
        return
    try:
        rows, missing = load_grid_rows(output_workbook)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        errors.append(f"output workbook could not be read: {exc}")
        return
    if missing:
        errors.append("output workbook missing columns: " + ", ".join(missing))
    if expected_rows > 0 and len(rows) != expected_rows:
        errors.append(f"output workbook row count mismatch: {len(rows)} != {expected_rows}")
    if not rows:
        errors.append("output workbook has no rows")
    elif all(not any(str(value or "").strip() for value in row.values()) for row in rows):
        warnings.append("output workbook rows are all blank")


def load_json_file(path: Path | None, errors: list[str], *, label: str) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists() or not path.is_file():
        errors.append(f"{label} missing: {path}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label} could not be read: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{label} must be a JSON object")
        return {}
    return data


def normalize_path(value: object) -> str:
    if value in (None, ""):
        return ""
    return os.path.normcase(os.path.normpath(str(Path(str(value)).resolve())))


def int_value(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def write_or_print_report(report: dict[str, Any], output_json: Path | None) -> None:
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if output_json is None:
        print(output)
        return
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(output + "\n", encoding="utf-8")


def validate_checker_output_path(
    output_json: Path | None,
    *,
    allow_repo_output: bool,
    smoke_output_dir: str,
) -> None:
    if output_json is None or allow_repo_output:
        return
    resolved = output_json.resolve()
    allowed_roots = [
        (ROOT / ".analysis_tmp").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    if smoke_output_dir:
        allowed_roots.append(Path(smoke_output_dir).resolve())
    if any(resolved == allowed or is_relative_to(resolved, allowed) for allowed in allowed_roots):
        return
    raise ValueError(
        "output_json must be under .analysis_tmp, the smoke output_dir, or temp; "
        "pass --allow-repo-output only for deliberate local experiments"
    )


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = check_live_smoke_workspace(args.manifest, min_processed=args.min_processed)
    try:
        validate_checker_output_path(
            args.output_json,
            allow_repo_output=args.allow_repo_output,
            smoke_output_dir=str(report.get("output_dir", "")),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    write_or_print_report(report, args.output_json)
    return 0 if report["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
