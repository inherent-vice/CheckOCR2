"""Run-report finalization helpers for OCR workflow execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .run_report import finalize_run_report, record_row_reports
from .workflow import WorkflowResult, finalize_processing_states


def finalize_workflow_report_success(
    *,
    report: dict[str, Any],
    rows: list[dict[str, Any]],
    row_timing_by_index: dict[int, dict[str, Any]],
    row_metadata_by_index: dict[int, dict[str, Any]],
    result: WorkflowResult,
    flush_report: Callable[[], None],
) -> None:
    finalize_processing_states(rows)
    record_row_reports(
        report,
        rows,
        row_timing_by_index,
        row_metadata_by_index,
    )
    finalize_run_report(
        report,
        rows,
        processed_count=result.processed_count,
        total_items=result.total_items,
        stopped=result.stopped,
    )
    flush_report()


def finalize_workflow_report_failure(
    *,
    report: dict[str, Any],
    rows: list[dict[str, Any]],
    error: str,
    flush_report: Callable[[], None],
) -> None:
    finalize_processing_states(rows)
    finalize_run_report(
        report,
        rows,
        processed_count=0,
        total_items=len(rows),
        stopped=True,
        error=error,
    )
    flush_report()
