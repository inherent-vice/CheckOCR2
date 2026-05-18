"""Pure row operations for the OCR grid."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Any

from .events import GridUpdate
from .models import (
    CODE_COL,
    DATE_COL,
    ERROR_STATUS_KEYWORDS,
    ERROR_STATUS_VALUES,
    NAME_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_DONE,
    STATUS_PROCESSING,
    STATUS_STOPPED,
    STATUS_WAITING,
)


@dataclass(frozen=True)
class ClipboardSelection:
    text: str
    count: int

    @property
    def has_items(self) -> bool:
        return self.count > 0


@dataclass(frozen=True)
class GridStatusSummary:
    total: int
    completed: int
    waiting: int
    errors: int

    @property
    def progress_percent(self) -> float:
        return (self.completed / self.total * 100) if self.total else 0.0


@dataclass(frozen=True)
class GridUpdateResult:
    row_index: int | None = None
    should_refresh: bool = False
    should_scroll: bool = False


GRID_RENDER_COLUMNS = (CODE_COL, NAME_COL, DATE_COL, RATE_COL, STATUS_COL)


def empty_row() -> dict[str, str]:
    return {CODE_COL: "", NAME_COL: "", DATE_COL: "", RATE_COL: "", STATUS_COL: STATUS_WAITING}


def rows_from_clipboard(clipboard_content: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in clipboard_content.strip().split("\n"):
        parts = line.split("\t")
        if parts and parts[0].strip():
            row = empty_row()
            row[CODE_COL] = parts[0].strip()
            row[NAME_COL] = parts[1].strip() if len(parts) > 1 else ""
            rows.append(row)
    return rows


def delete_rows(rows: list[dict[str, str]], indices_to_delete: list[int]) -> None:
    for index in sorted(indices_to_delete, reverse=True):
        if 0 <= index < len(rows):
            del rows[index]


def row_for_copy(row: dict[str, str]) -> str:
    return "\t".join(
        [
            grid_cell_text(row.get(CODE_COL, "")),
            grid_cell_text(row.get(NAME_COL, "")),
            grid_cell_text(row.get(DATE_COL, "")),
            grid_cell_text(row.get(RATE_COL, "")),
            grid_cell_text(row.get(STATUS_COL, "")),
        ]
    )


def rows_for_copy(rows: list[dict[str, str]], indices: list[int]) -> ClipboardSelection:
    copied_rows = [row_for_copy(rows[index]) for index in indices if 0 <= index < len(rows)]
    return ClipboardSelection(text="\n".join(copied_rows), count=len(copied_rows))


def rates_for_copy(rows: list[dict[str, str]], indices: list[int]) -> ClipboardSelection:
    copied_rates = [grid_cell_text(rows[index].get(RATE_COL, "")) for index in indices if 0 <= index < len(rows)]
    return ClipboardSelection(text="\n".join(copied_rates), count=len(copied_rates))


def apply_grid_update(rows: list[dict[str, Any]], update: GridUpdate) -> GridUpdateResult:
    update_type = update.update_type
    grid_idx = update.row_index
    payload = update.payload
    if not 0 <= grid_idx < len(rows):
        return GridUpdateResult()

    row = rows[grid_idx]
    should_scroll = False
    if update_type == "processing":
        row[STATUS_COL] = STATUS_PROCESSING
        should_scroll = True
    elif update_type == "complete" and len(payload) >= 3:
        date_result, rate_result, status_result = payload[0], payload[1], payload[2]
        if date_result is not None:
            row[DATE_COL] = date_result
        if rate_result is not None:
            row[RATE_COL] = rate_result
        row[STATUS_COL] = status_result
    elif update_type == "error" and len(payload) >= 1:
        row[STATUS_COL] = payload[0]

    return GridUpdateResult(row_index=grid_idx, should_refresh=True, should_scroll=should_scroll)


def status_is_error(status: str) -> bool:
    return status in ERROR_STATUS_VALUES or any(keyword in status for keyword in ERROR_STATUS_KEYWORDS)


def grid_row_values(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        grid_cell_text(row[CODE_COL]),
        grid_cell_text(row[NAME_COL]),
        grid_cell_text(row[DATE_COL]),
        grid_cell_text(row[RATE_COL]),
        grid_cell_text(row[STATUS_COL]),
    )


def grid_row_tags(
    row: dict[str, str],
    *,
    row_index: int,
    current_processing_index: int,
    is_running: bool,
) -> tuple[str, ...]:
    status = row.get(STATUS_COL, "")
    if status == STATUS_DONE:
        return ("completed",)
    if status_is_error(status):
        return ("error",)
    if row_index == current_processing_index and is_running:
        return ("processing",)
    return ()


def summarize_grid_rows(rows: list[dict[str, str]]) -> GridStatusSummary:
    """Summarize the status of all rows in a single pass."""
    total = len(rows)
    completed = 0
    waiting = 0
    errors = 0

    for row in rows:
        status = row.get(STATUS_COL, "")
        if status == STATUS_DONE:
            completed += 1
        elif status == STATUS_WAITING:
            waiting += 1
        elif status_is_error(status):
            errors += 1

    return GridStatusSummary(
        total=total,
        completed=completed,
        waiting=waiting,
        errors=errors,
    )


def format_grid_status_text(summary: GridStatusSummary) -> str:
    return (
        f"총 {summary.total}행 | 완료: {summary.completed} | "
        f"대기: {summary.waiting} | 오류: {summary.errors}"
    )


def format_grid_progress_text(summary: GridStatusSummary) -> str:
    return f"진행률: {summary.progress_percent:.1f}%"


def rows_for_export(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    export_rows: list[dict[str, str]] = []
    for row in rows:
        export_row = {
            CODE_COL: grid_cell_text(row.get(CODE_COL, "")),
            NAME_COL: grid_cell_text(row.get(NAME_COL, "")),
            DATE_COL: grid_cell_text(row.get(DATE_COL, "")),
            RATE_COL: grid_cell_text(row.get(RATE_COL, "")),
            STATUS_COL: grid_cell_text(row.get(STATUS_COL, "")),
        }
        if export_row[STATUS_COL] == STATUS_STOPPED:
            export_row[STATUS_COL] = ""
        export_rows.append(export_row)
    return export_rows


def grid_cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Real):
        try:
            if math.isnan(float(value)):
                return ""
        except (OverflowError, ValueError):
            pass
    return str(value)
