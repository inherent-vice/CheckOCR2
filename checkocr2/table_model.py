"""Pure row operations for the OCR grid."""

from __future__ import annotations

from .models import (
    CODE_COL,
    DATE_COL,
    NAME_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_STOPPED,
    STATUS_WAITING,
)


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
            row.get(CODE_COL, ""),
            row.get(NAME_COL, ""),
            row.get(DATE_COL, ""),
            row.get(RATE_COL, ""),
            row.get(STATUS_COL, ""),
        ]
    )


def rows_for_export(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    export_rows: list[dict[str, str]] = []
    for row in rows:
        export_row = {
            CODE_COL: row.get(CODE_COL, ""),
            NAME_COL: row.get(NAME_COL, ""),
            DATE_COL: row.get(DATE_COL, ""),
            RATE_COL: row.get(RATE_COL, ""),
            STATUS_COL: row.get(STATUS_COL, ""),
        }
        if export_row[STATUS_COL] == STATUS_STOPPED:
            export_row[STATUS_COL] = ""
        export_rows.append(export_row)
    return export_rows
