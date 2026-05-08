from __future__ import annotations

from checkocr2.models import (
    CODE_COL,
    DATE_COL,
    NAME_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_DONE,
    STATUS_STOPPED,
)
from checkocr2.workflow import (
    ERROR_CAPTURE_FAILED,
    CapturedImages,
    FakeAutomationAdapter,
    FakeOcrAdapter,
    FinalizationIntent,
    OcrResult,
    WorkflowContext,
    WorkflowOptions,
    WorkflowRunner,
    WorkflowStopToken,
    finalize_processing_states,
)


def make_row(code: str, name: str = "Name") -> dict[str, str]:
    return {CODE_COL: code, NAME_COL: name, DATE_COL: "", RATE_COL: "", STATUS_COL: ""}


def test_workflow_success_updates_grid_row_and_emits_legacy_compatible_events():
    rows = [make_row("A001", "Alpha")]
    automation = FakeAutomationAdapter()
    timing = {"ocr_timing_ms": {"date_ocr_ms": 1.2}}
    ocr = FakeOcrAdapter({"A001": OcrResult("2026/05/08", "3.500", metadata={"timing_ms": timing})})
    runner = WorkflowRunner(automation, ocr)

    result = runner.process_rows(
        rows,
        WorkflowOptions(output_dir="out", input_excel_path="source.xlsx"),
    )

    assert result.processed_count == 1
    assert result.total_items == 1
    assert result.finalization_intent == FinalizationIntent("out", "source.xlsx", 1, 1)
    assert rows[0][DATE_COL] == "2026/05/08"
    assert rows[0][RATE_COL] == "3.500"
    assert rows[0][STATUS_COL] == STATUS_DONE
    assert "update_ms" in timing
    assert runner.legacy_tuples() == [
        ("grid_update", ("processing", 0)),
        ("grid_update", ("complete", 0, "2026/05/08", "3.500", STATUS_DONE)),
        ("log", "[A001] complete - date: '2026/05/08', rate: '3.500'", "SUCCESS"),
        ("finalize_export_and_complete", "out", "source.xlsx", 1, 1),
    ]
    assert automation.calls[0][1] == WorkflowContext(
        index=0,
        total_items=1,
        output_dir="out",
        input_excel_path="source.xlsx",
        save_detail_images=True,
    )


def test_workflow_kbp_skip_completes_without_capture_or_ocr():
    rows = [make_row("KBP123")]
    automation = FakeAutomationAdapter()
    ocr = FakeOcrAdapter()
    runner = WorkflowRunner(automation, ocr)

    result = runner.process_rows(rows, WorkflowOptions(skip_kbp_code=True))

    assert result.processed_count == 1
    assert rows[0][DATE_COL] == ""
    assert rows[0][RATE_COL] == ""
    assert rows[0][STATUS_COL] == STATUS_DONE
    assert automation.calls == []
    assert ocr.calls == []
    assert ("grid_update", ("complete", 0, "", "", STATUS_DONE)) in runner.legacy_tuples()


def test_workflow_capture_failure_marks_error_and_still_requests_finalization():
    rows = [make_row("A001")]
    automation = FakeAutomationAdapter({"A001": None})
    runner = WorkflowRunner(automation, FakeOcrAdapter())

    result = runner.process_rows(rows, WorkflowOptions(output_dir="out"))

    assert result.processed_count == 0
    assert result.finalization_intent == FinalizationIntent("out", "", 0, 1)
    assert rows[0][STATUS_COL] == ERROR_CAPTURE_FAILED
    assert runner.legacy_tuples() == [
        ("grid_update", ("processing", 0)),
        ("grid_update", ("error", 0, ERROR_CAPTURE_FAILED)),
        ("finalize_export_and_complete", "out", "", 0, 1),
    ]


def test_workflow_stop_emits_stopped_event_without_finalization_intent():
    class StopAfterCapture:
        def __init__(self, token: WorkflowStopToken) -> None:
            self.token = token

        def capture(self, row, context):
            self.token.stop()
            return CapturedImages("date-image", "rate-image")

    rows = [make_row("A001"), make_row("A002")]
    token = WorkflowStopToken()
    runner = WorkflowRunner(StopAfterCapture(token), FakeOcrAdapter(), stop_token=token)

    result = runner.process_rows(rows)

    assert result.stopped is True
    assert result.finalization_intent is None
    assert token.current_item == "A001 (Name)"
    assert runner.legacy_tuples() == [
        ("grid_update", ("processing", 0)),
        ("log", "Workflow stopped.", "INFO"),
        ("stopped", None),
    ]


def test_finalize_processing_states_uses_package_status_constants():
    rows = [make_row("A001"), make_row("A002")]
    rows[0][STATUS_COL] = STATUS_DONE

    changed = finalize_processing_states(rows)

    assert changed == 1
    assert rows[0][STATUS_COL] == STATUS_DONE
    assert rows[1][STATUS_COL] == STATUS_STOPPED
