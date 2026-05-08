from __future__ import annotations

import pandas as pd

from checkocr2.excel_io import export_grid_rows, load_grid_rows, resolve_columns
from checkocr2.models import CODE_COL, DATE_COL, NAME_COL, RATE_COL, STATUS_COL, STATUS_STOPPED
from checkocr2.table_model import delete_rows, row_for_copy, rows_for_export, rows_from_clipboard


def test_resolve_columns_accepts_korean_and_english_aliases():
    resolved, missing = resolve_columns(["code", "회사명"])

    assert missing == []
    assert resolved[CODE_COL] == "code"
    assert resolved[NAME_COL] == "회사명"


def test_table_model_clipboard_delete_copy_and_export_status():
    rows = rows_from_clipboard("A001\tAlpha\nB002\tBeta")

    assert row_for_copy(rows[0]) == "A001\tAlpha\t\t\t대기 중"

    rows[1][STATUS_COL] = STATUS_STOPPED
    export_rows = rows_for_export(rows)
    assert export_rows[1][STATUS_COL] == ""

    delete_rows(rows, [0])
    assert rows[0][CODE_COL] == "B002"


def test_excel_io_loads_and_exports_grid_rows(tmp_path):
    source = tmp_path / "source.xlsx"
    pd.DataFrame([{"code": "A001", "name": "Alpha"}]).to_excel(source, index=False)

    rows, missing = load_grid_rows(source)

    assert missing == []
    assert rows == [{CODE_COL: "A001", NAME_COL: "Alpha", DATE_COL: "", RATE_COL: "", STATUS_COL: "대기 중"}]

    rows[0][DATE_COL] = "2026/05/08"
    rows[0][RATE_COL] = "3.500"
    output = export_grid_rows(rows, tmp_path / "out.xlsx")
    exported = pd.read_excel(output, dtype=str).fillna("")

    assert exported.to_dict("records")[0][CODE_COL] == "A001"
    assert exported.to_dict("records")[0][RATE_COL] == "3.500"
