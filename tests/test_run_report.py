from __future__ import annotations

import json

from checkocr2.models import CODE_COL, DATE_COL, NAME_COL, RATE_COL, STATUS_COL, STATUS_DONE
from checkocr2.run_report import (
    create_run_report,
    finalize_run_report,
    record_row_reports,
    report_output_path,
    write_run_report,
)


def test_report_output_path_uses_input_stem_next_to_excel_output(tmp_path):
    output = report_output_path(tmp_path, r"C:\input\sample.xlsx")

    assert output == tmp_path / "sample_run_report.json"


def test_finalize_run_report_counts_blank_fields_and_writes_json(tmp_path):
    rows = [
        {CODE_COL: "A001", NAME_COL: "Alpha", DATE_COL: "2026/05/08", RATE_COL: "3.500", STATUS_COL: STATUS_DONE},
        {CODE_COL: "A002", NAME_COL: "Beta", DATE_COL: "", RATE_COL: "4.000", STATUS_COL: "capture failed"},
    ]
    report = create_run_report(
        output_dir=str(tmp_path),
        input_excel_path="source.xlsx",
        total_items=len(rows),
        save_detail_images=False,
    )

    record_row_reports(
        report,
        rows,
        {0: {"capture_timing_ms": {"click_ms": 1.2}}},
        {
            0: {
                "ocr_confidence": {"date_confidence": 0.9},
                "ocr_fallback": {
                    "date_fallback_count": 1,
                    "actual_ocr_engine": "paddle",
                    "ocr_fallback_engine": "easyocr",
                },
            }
        },
    )
    finalize_run_report(
        report,
        rows,
        processed_count=1,
        total_items=2,
        stopped=False,
        output_workbook_path=tmp_path / "source_updated.xlsx",
        export_timing_ms={"export_ms": 3.4},
    )
    report_path = write_run_report(report, tmp_path / "source_run_report.json")

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["summary"]["blank_date_count"] == 1
    assert data["summary"]["blank_rate_count"] == 0
    assert data["summary"]["status_counts"][STATUS_DONE] == 1
    assert data["summary"]["status_counts"]["capture failed"] == 1
    assert data["summary"]["output_workbook_path"].endswith("source_updated.xlsx")
    assert data["summary"]["export_timing_ms"] == {"export_ms": 3.4}
    assert data["summary"]["ocr_fallback_count"] == 1
    assert data["summary"]["ocr_fallback_rows"] == 1
    assert data["rows"][0]["timing_ms"]["capture_timing_ms"]["click_ms"] == 1.2
    assert data["rows"][0]["ocr_confidence"] == {"date_confidence": 0.9}
    assert data["rows"][0]["ocr_fallback"]["total_count"] == 1
    assert data["rows"][1]["blank_fields"] == ["date"]
    assert data["rows"][1]["failure_reason"] == "capture failed"
