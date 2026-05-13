"""JSON run report helpers for OCR timing and outcome evidence."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import CODE_COL, DATE_COL, NAME_COL, RATE_COL, STATUS_COL, STATUS_DONE

SCHEMA_VERSION = 1


def report_output_path(output_dir: str | os.PathLike[str], input_excel_path: str | None) -> Path:
    """Return the JSON report path next to the exported Excel workbook."""

    base_name = os.path.basename(input_excel_path) if input_excel_path else "ocr_results"
    stem = os.path.splitext(base_name)[0] or "ocr_results"
    return Path(output_dir) / f"{stem}_run_report.json"


def create_run_report(
    *,
    output_dir: str,
    input_excel_path: str,
    total_items: int,
    save_detail_images: bool,
) -> dict[str, Any]:
    """Create the base run report document."""

    return {
        "schema_version": SCHEMA_VERSION,
        "started_at": _now_iso(),
        "completed_at": None,
        "input_excel_path": input_excel_path,
        "output_dir": output_dir,
        "options": {"save_detail_images": save_detail_images},
        "summary": {
            "processed_count": 0,
            "total_items": total_items,
            "stopped": False,
            "blank_date_count": 0,
            "blank_rate_count": 0,
            "status_counts": {},
        },
        "rows": [],
        "errors": [],
    }


def record_row_reports(
    report: dict[str, Any],
    rows: list[dict[str, Any]],
    row_timing_by_index: dict[int, dict[str, Any]],
    row_metadata_by_index: dict[int, dict[str, Any]] | None = None,
) -> None:
    """Replace row reports with current grid outcomes and collected timing."""

    metadata_by_index = row_metadata_by_index or {}
    report["rows"] = [
        _row_report(index, row, row_timing_by_index.get(index, {}), metadata_by_index.get(index, {}))
        for index, row in enumerate(rows)
    ]


def finalize_run_report(
    report: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    processed_count: int,
    total_items: int,
    stopped: bool,
    output_workbook_path: str | os.PathLike[str] | None = None,
    export_timing_ms: dict[str, float] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Update summary fields after workflow or export finalization."""

    report["completed_at"] = _now_iso()
    summary = report.setdefault("summary", {})
    summary.update(
        {
            "processed_count": processed_count,
            "total_items": total_items,
            "stopped": stopped,
            "blank_date_count": sum(1 for row in rows if not str(row.get(DATE_COL, "") or "").strip()),
            "blank_rate_count": sum(1 for row in rows if not str(row.get(RATE_COL, "") or "").strip()),
            "status_counts": dict(Counter(str(row.get(STATUS_COL, "") or "") for row in rows)),
        }
    )
    if output_workbook_path is not None:
        summary["output_workbook_path"] = str(output_workbook_path)
    if export_timing_ms is not None:
        summary["export_timing_ms"] = export_timing_ms
    if error:
        report.setdefault("errors", []).append(error)
    fallback_count = sum(
        int(row.get("ocr_fallback", {}).get("total_count", 0) or 0)
        for row in report.get("rows", [])
        if isinstance(row.get("ocr_fallback"), dict)
    )
    summary["ocr_fallback_count"] = fallback_count
    summary["ocr_fallback_rows"] = sum(
        1
        for row in report.get("rows", [])
        if isinstance(row.get("ocr_fallback"), dict)
        and int(row.get("ocr_fallback", {}).get("total_count", 0) or 0) > 0
    )
    return report


def write_run_report(report: dict[str, Any], path: str | os.PathLike[str]) -> Path:
    """Write the report as UTF-8 JSON and replace existing content atomically."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f"{output_path.name}.tmp")
    temp_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(output_path)
    return output_path


def _row_report(
    index: int,
    row: dict[str, Any],
    timing: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    date = str(row.get(DATE_COL, "") or "")
    rate = str(row.get(RATE_COL, "") or "")
    status = str(row.get(STATUS_COL, "") or "")
    blank_fields = []
    if not date.strip():
        blank_fields.append("date")
    if not rate.strip():
        blank_fields.append("rate")

    report = {
        "index": index,
        "code": str(row.get(CODE_COL, "") or ""),
        "name": str(row.get(NAME_COL, "") or ""),
        "date": date,
        "rate": rate,
        "status": status,
        "blank_fields": blank_fields,
        "failure_reason": "" if status == STATUS_DONE else status,
        "timing_ms": timing,
    }
    if metadata.get("ocr_confidence"):
        report["ocr_confidence"] = metadata["ocr_confidence"]
    if metadata.get("ocr_fallback"):
        fallback = dict(metadata["ocr_fallback"])
        total_count = sum(
            int(fallback.get(key, 0) or 0)
            for key in ("date_fallback_count", "rate_fallback_count")
        )
        fallback["total_count"] = total_count
        report["ocr_fallback"] = fallback
    return report


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
