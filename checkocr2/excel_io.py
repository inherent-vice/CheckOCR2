"""Excel import/export helpers for the OCR grid."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from .exceptions import ExcelIOError
from .models import CODE_COL, DATE_COL, NAME_COL, RATE_COL, STATUS_COL
from .ocr_runtime_options import DEFAULT_RATE_DECIMAL_PLACES, normalize_rate_decimal_places
from .table_model import empty_row, rows_for_export

COLUMN_ALIASES = {
    CODE_COL: ["종목코드", "code", "item code"],
    NAME_COL: ["종목명", "name", "item name", "회사명"],
}


def resolve_columns(columns: list[object]) -> tuple[dict[str, str | None], list[str]]:
    column_lookup = {str(column).lower(): str(column) for column in columns}
    resolved: dict[str, str | None] = {}
    missing: list[str] = []
    for target_col, aliases in COLUMN_ALIASES.items():
        resolved[target_col] = None
        for alias in aliases:
            if alias in column_lookup:
                resolved[target_col] = column_lookup[alias]
                break
        if resolved[target_col] is None:
            missing.append(target_col)
    return resolved, missing


def load_grid_rows(file_path: str | os.PathLike[str]) -> tuple[list[dict[str, str]], list[str]]:
    try:
        df = pd.read_excel(file_path, dtype=str)
    except Exception as exc:
        raise ExcelIOError(f"Excel file could not be read: {exc}") from exc
    col_map, missing = resolve_columns(list(df.columns))

    rows: list[dict[str, str]] = []
    for _, source_row in df.iterrows():
        row = empty_row()
        code_col = col_map.get(CODE_COL)
        name_col = col_map.get(NAME_COL)
        if code_col and code_col in source_row:
            row[CODE_COL] = _excel_cell_text(source_row[code_col])
        if name_col and name_col in source_row:
            row[NAME_COL] = _excel_cell_text(source_row[name_col])
        rows.append(row)
    return rows, missing


def export_grid_rows(
    rows: list[dict[str, str]],
    output_path: str | os.PathLike[str],
    *,
    rate_decimal_places: int = DEFAULT_RATE_DECIMAL_PLACES,
) -> Path:
    output = Path(output_path)
    try:
        export_rows = rows_for_export(rows)
        df_export = pd.DataFrame(export_rows)
        df_export = df_export[[CODE_COL, NAME_COL, DATE_COL, RATE_COL, STATUS_COL]]
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export.to_excel(writer, sheet_name="OCR_Results", index=False)
            worksheet = writer.sheets["OCR_Results"]
            apply_output_cell_formats(
                worksheet,
                export_rows,
                rate_decimal_places=rate_decimal_places,
            )
    except Exception as exc:
        raise ExcelIOError(f"Excel file could not be written: {exc}") from exc
    return output


def apply_output_cell_formats(
    worksheet: Worksheet,
    rows: list[dict[str, str]],
    *,
    rate_decimal_places: int = DEFAULT_RATE_DECIMAL_PLACES,
) -> None:
    date_col = 3
    rate_col = 4
    rate_format = rate_number_format(rate_decimal_places)
    for row_index, row in enumerate(rows, start=2):
        date_cell = worksheet.cell(row=row_index, column=date_col)
        date_cell.number_format = "yyyy/mm/dd"
        parsed_date = parse_output_date(row.get(DATE_COL, ""))
        if parsed_date is not None:
            date_cell.value = parsed_date

        rate_cell = worksheet.cell(row=row_index, column=rate_col)
        rate_cell.number_format = rate_format
        parsed_rate = parse_output_rate(row.get(RATE_COL, ""))
        if parsed_rate is not None:
            rate_cell.value = parsed_rate


def rate_number_format(rate_decimal_places: int) -> str:
    precision = normalize_rate_decimal_places(rate_decimal_places)
    return "0" if precision <= 0 else "0." + ("0" * precision)


def parse_output_date(value: object):
    text = _excel_cell_text(value).strip()
    if not text:
        return None
    for date_format in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def parse_output_rate(value: object) -> float | None:
    text = _excel_cell_text(value).strip().replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _excel_cell_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)
