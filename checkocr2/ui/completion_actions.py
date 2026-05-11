"""Work completion actions for the legacy Tk shell."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from tkinter import messagebox
from typing import Any

from checkocr2.exceptions import ExcelIOError
from checkocr2.paths import updated_workbook_path
from checkocr2.run_report import finalize_run_report, record_row_reports


def build_ocr_summary(rows: list[dict[str, object]], total_items: int) -> str:
    actual_processed_for_stats = sum(1 for row in rows if row["상태"] == "완료")
    return f"""📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: {total_items}개
        성공적으로 처리된 항목: {actual_processed_for_stats}개
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """


def finalize_export_and_complete(
    app: Any,
    output_dir_str: str,
    input_excel_path_str: str,
    summary_message: str,
    *,
    report_manager: Any | None = None,
    reset_work_state: bool = True,
    showerror: Callable[..., object] | None = None,
    showinfo: Callable[..., object] | None = None,
    clock: Callable[[], float] = perf_counter,
    workbook_path_factory: Callable[[str, str], Path] = updated_workbook_path,
) -> None:
    app.logger.info("[_finalize_export_and_complete] 함수 호출됨 (Main Thread)")
    app._finalize_processing_states()

    export_started = clock()
    export_error = None
    output_workbook = workbook_path_factory(output_dir_str, input_excel_path_str)
    try:
        output_workbook = (
            app.data_manager.export_grid_to_excel_data(
                output_dir_str, input_excel_path_str
            )
            or output_workbook
        )
    except (OSError, ValueError, ImportError, ExcelIOError) as export_exc:
        export_error = f"Excel export failed: {export_exc}"
    export_timing_ms = {"export_ms": round((clock() - export_started) * 1000, 3)}

    report_manager = (
        report_manager
        if report_manager is not None
        else getattr(app, "ocr_workflow_manager", app)
    )
    current_report = getattr(report_manager, "_current_run_report", None)
    if current_report is not None:
        existing_timings = {
            row_report.get("index"): row_report.get("timing_ms", {})
            for row_report in current_report.get("rows", [])
        }
        existing_metadata = {
            row_report.get("index"): {
                "ocr_confidence": row_report.get("ocr_confidence")
            }
            for row_report in current_report.get("rows", [])
            if row_report.get("ocr_confidence")
        }
        record_row_reports(
            current_report,
            app.data_manager.excel_data,
            existing_timings,
            existing_metadata,
        )
        summary = current_report.get("summary", {})
        if export_error is None and not output_workbook.exists():
            export_error = (
                f"Export workbook was not found after export: {output_workbook}"
            )
        finalize_run_report(
            current_report,
            app.data_manager.excel_data,
            processed_count=int(summary.get("processed_count", 0) or 0),
            total_items=int(
                summary.get("total_items", len(app.data_manager.excel_data)) or 0
            ),
            stopped=bool(summary.get("stopped", False)),
            output_workbook_path=output_workbook,
            export_timing_ms=export_timing_ms,
            error=export_error,
        )
        report_manager._flush_current_run_report()

    if reset_work_state:
        app.work_controller.reset()
        app.data_manager.current_processing_index = -1
        app._set_runtime_state(app._ready_or_error_state())

    app.refresh_grid_ui()

    if export_error is not None:
        (showerror or messagebox.showerror)("Excel export failed", export_error)
        return
    (showinfo or messagebox.showinfo)("처리 완료", summary_message)


def complete_work(app: Any, summary_message: str) -> None:
    app.logger.info("[_on_work_complete_ui_only] 함수 호출됨 (Main Thread)")
    app.work_controller.reset()
    app.data_manager.current_processing_index = -1
    app._set_runtime_state(app._ready_or_error_state())
    app.refresh_grid_ui()
    app.quick_save_settings()


def complete_stopped_work(app: Any) -> None:
    app.logger.info("[_on_work_stopped] 함수 호출됨 (Main Thread)")
    app.work_controller.reset()
    app.data_manager.current_processing_index = -1
    app._set_runtime_state(app._ready_or_error_state())
    app._finalize_processing_states()
    app.refresh_grid_ui()
    messagebox.showinfo("중단됨", "작업이 사용자에 의해 중단되었습니다.")
