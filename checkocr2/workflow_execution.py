"""Workflow execution assembly for the legacy OCR manager."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from checkocr2.workflow import WorkflowOptions, WorkflowRunner
from checkocr2.workflow import finalize_processing_states as finalize_workflow_processing_states
from checkocr2.workflow_event_bridge import WorkflowEventBridge
from checkocr2.workflow_legacy_adapters import LegacyAutomationAdapter, LegacyEasyOcrAdapter
from checkocr2.workflow_report_finalization import finalize_workflow_report_success
from checkocr2.workflow_run_setup import WorkflowRunSetup, prepare_workflow_run


@dataclass(frozen=True)
class WorkflowExecutionCallbacks:
    capture_screenshots: Callable[..., tuple[Any, Any]]
    process_single_ocr: Callable[..., tuple[str, str]]
    clear_ocr_tracking: Callable[[], None]
    get_capture_timing: Callable[[], dict[str, Any]]
    get_ocr_timings: Callable[[], dict[str, Any]]
    get_ocr_confidences: Callable[[], dict[str, Any]]
    elapsed_ms: Callable[[float], float]
    flush_report: Callable[[], None]
    set_current_run_report: Callable[[dict[str, Any], Any], None]


def execute_legacy_workflow(
    *,
    ui_settings: dict[str, Any],
    output_dir: str,
    input_excel_file: str,
    rows: list[dict[str, Any]],
    save_detail_images: bool,
    skip_kbp_code: bool,
    message_queue: Any,
    data_manager: Any,
    work_controller: Any,
    logger: Any,
    callbacks: WorkflowExecutionCallbacks,
) -> WorkflowRunSetup:
    """Build and run the legacy workflow adapters for one OCR run."""

    run_setup = prepare_workflow_run(
        ui_settings,
        output_dir,
        input_excel_file,
        len(rows),
        save_detail_images,
    )
    callbacks.set_current_run_report(run_setup.report, run_setup.report_path)

    row_timing_by_index: dict[int, dict[str, Any]] = {}
    row_metadata_by_index: dict[int, dict[str, Any]] = {}
    event_bridge = WorkflowEventBridge(
        message_queue,
        data_manager,
        row_timing_by_index,
        callbacks.elapsed_ms,
    )

    runner = WorkflowRunner(
        LegacyAutomationAdapter(
            callbacks.capture_screenshots,
            run_setup.save_folder,
            run_setup.coords,
            run_setup.paste_delay,
            run_setup.load_delay,
            save_detail_images,
            callbacks.get_capture_timing,
            row_timing_by_index,
            callbacks.elapsed_ms,
        ),
        LegacyEasyOcrAdapter(
            callbacks.process_single_ocr,
            save_detail_images,
            callbacks.clear_ocr_tracking,
            callbacks.get_ocr_timings,
            callbacks.get_ocr_confidences,
            row_timing_by_index,
            row_metadata_by_index,
            callbacks.elapsed_ms,
        ),
        stop_token=work_controller,
        event_sink=event_bridge.emit,
    )
    result = runner.process_rows(
        rows,
        WorkflowOptions(
            skip_kbp_code=skip_kbp_code,
            save_detail_images=save_detail_images,
            output_dir=output_dir,
            input_excel_path=input_excel_file,
        ),
    )

    if result.stopped:
        finalize_workflow_processing_states(rows)
        logger.info("[OCRWorkflowManager] 작업 루프 종료됨 (사용자 중단).")
    else:
        logger.info("[OCRWorkflowManager] 모든 항목 처리 완료. 최종 처리 메시지 전송 중.")

    finalize_workflow_report_success(
        report=run_setup.report,
        rows=rows,
        row_timing_by_index=row_timing_by_index,
        row_metadata_by_index=row_metadata_by_index,
        result=result,
        flush_report=callbacks.flush_report,
    )
    return run_setup
