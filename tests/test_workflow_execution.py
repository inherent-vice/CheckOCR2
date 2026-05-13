from __future__ import annotations

import logging
import queue
from types import SimpleNamespace

from checkocr2.models import CODE_COL, DATE_COL, NAME_COL, RATE_COL, STATUS_COL, STATUS_DONE
from checkocr2.work_controller import WorkController
from checkocr2.workflow_execution import WorkflowExecutionCallbacks, execute_legacy_workflow


def test_execute_legacy_workflow_assembles_adapters_and_finalizes_report(tmp_path):
    rows = [
        {
            CODE_COL: "A001",
            NAME_COL: "Alpha",
            DATE_COL: "",
            RATE_COL: "",
            STATUS_COL: "",
        }
    ]
    events = queue.Queue()
    data_manager = SimpleNamespace(current_processing_index=None)
    selected_reports = []
    flushed = []

    callbacks = WorkflowExecutionCallbacks(
        capture_screenshots=lambda *_args: ("date-image", "rate-image"),
        process_single_ocr=lambda *_args: ("2026/05/08", "3.500"),
        clear_ocr_tracking=lambda: None,
        get_capture_timing=lambda: {"screen_capture_ms": 1.0},
        get_ocr_timings=lambda: {"date_ocr_ms": 2.0, "rate_ocr_ms": 3.0},
        get_ocr_confidences=lambda: {"date_confidence": 0.91},
        get_ocr_fallbacks=lambda: {"date_fallback_count": 1},
        elapsed_ms=lambda _started_at: 4.0,
        flush_report=lambda: flushed.append(True),
        set_current_run_report=lambda report, path: selected_reports.append((report, path)),
    )

    run_setup = execute_legacy_workflow(
        ui_settings={
            "delays": {"paste": 0, "loading": 0},
            "click_point": (1, 1),
            "all_area": (0, 0, 20, 20),
            "date_area": (0, 0, 10, 10),
            "rate_area": (10, 10, 20, 20),
        },
        output_dir=str(tmp_path),
        input_excel_file=str(tmp_path / "source.xlsx"),
        rows=rows,
        save_detail_images=False,
        skip_kbp_code=True,
        message_queue=events,
        data_manager=data_manager,
        work_controller=WorkController(),
        logger=logging.getLogger("tests.workflow_execution"),
        callbacks=callbacks,
    )

    assert rows[0][DATE_COL] == "2026/05/08"
    assert rows[0][RATE_COL] == "3.500"
    assert rows[0][STATUS_COL] == STATUS_DONE
    assert selected_reports == [(run_setup.report, run_setup.report_path)]
    assert flushed == [True]
    assert run_setup.report["summary"]["processed_count"] == 1
    assert run_setup.report["rows"][0]["ocr_confidence"] == {"date_confidence": 0.91}
    assert run_setup.report["rows"][0]["ocr_fallback"]["total_count"] == 1
