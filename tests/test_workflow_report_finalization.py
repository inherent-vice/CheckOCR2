from __future__ import annotations

from copy import deepcopy

from checkocr2.models import (
    CODE_COL,
    DATE_COL,
    NAME_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_DONE,
    STATUS_PROCESSING,
    STATUS_STOPPED,
)
from checkocr2.run_report import create_run_report
from checkocr2.workflow import WorkflowResult
from checkocr2.workflow_report_finalization import (
    finalize_workflow_report_failure,
    finalize_workflow_report_success,
)


def test_finalize_workflow_report_success_records_rows_summary_and_flushes(tmp_path):
    rows = [
        {
            CODE_COL: "A001",
            NAME_COL: "Alpha",
            DATE_COL: "2026/05/08",
            RATE_COL: "3.500",
            STATUS_COL: STATUS_DONE,
        }
    ]
    report = create_run_report(
        output_dir=str(tmp_path),
        input_excel_path=str(tmp_path / "source.xlsx"),
        total_items=1,
        save_detail_images=True,
    )
    flushed_reports = []

    finalize_workflow_report_success(
        report=report,
        rows=rows,
        row_timing_by_index={0: {"row_total_ms": 10.0}},
        row_metadata_by_index={0: {"ocr_confidence": {"date_confidence": 0.91}}},
        result=WorkflowResult(processed_count=1, total_items=1, stopped=False),
        flush_report=lambda: flushed_reports.append(deepcopy(report)),
    )

    assert report["summary"]["processed_count"] == 1
    assert report["summary"]["total_items"] == 1
    assert report["summary"]["stopped"] is False
    assert report["rows"][0]["timing_ms"] == {"row_total_ms": 10.0}
    assert report["rows"][0]["ocr_confidence"] == {"date_confidence": 0.91}
    assert flushed_reports == [report]


def test_finalize_workflow_report_success_finalizes_processing_rows(tmp_path):
    rows = [
        {
            CODE_COL: "A001",
            NAME_COL: "Alpha",
            DATE_COL: "",
            RATE_COL: "",
            STATUS_COL: STATUS_PROCESSING,
        }
    ]
    report = create_run_report(
        output_dir=str(tmp_path),
        input_excel_path=str(tmp_path / "source.xlsx"),
        total_items=1,
        save_detail_images=False,
    )

    finalize_workflow_report_success(
        report=report,
        rows=rows,
        row_timing_by_index={},
        row_metadata_by_index={},
        result=WorkflowResult(processed_count=0, total_items=1, stopped=True),
        flush_report=lambda: None,
    )

    assert rows[0][STATUS_COL] == STATUS_STOPPED
    assert report["summary"]["stopped"] is True
    assert report["summary"]["status_counts"] == {STATUS_STOPPED: 1}
    assert report["rows"][0]["status"] == STATUS_STOPPED
    assert report["rows"][0]["failure_reason"] == STATUS_STOPPED


def test_finalize_workflow_report_failure_records_error_and_flushes(tmp_path):
    rows = [
        {
            CODE_COL: "A001",
            NAME_COL: "Alpha",
            DATE_COL: "",
            RATE_COL: "",
            STATUS_COL: "",
        },
        {
            CODE_COL: "A002",
            NAME_COL: "Beta",
            DATE_COL: "",
            RATE_COL: "",
            STATUS_COL: STATUS_DONE,
        },
    ]
    report = create_run_report(
        output_dir=str(tmp_path),
        input_excel_path=str(tmp_path / "source.xlsx"),
        total_items=2,
        save_detail_images=False,
    )
    flushed_reports = []

    finalize_workflow_report_failure(
        report=report,
        rows=rows,
        error="boom",
        flush_report=lambda: flushed_reports.append(deepcopy(report)),
    )

    assert report["summary"]["processed_count"] == 0
    assert report["summary"]["total_items"] == 2
    assert report["summary"]["stopped"] is True
    assert report["errors"] == ["boom"]
    assert rows[0][STATUS_COL] == STATUS_STOPPED
    assert report["summary"]["status_counts"] == {STATUS_STOPPED: 1, STATUS_DONE: 1}
    assert flushed_reports == [report]
