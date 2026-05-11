from __future__ import annotations

from types import SimpleNamespace

from checkocr2.runtime_state import RuntimeState
from checkocr2.ui import completion_actions


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


class FakeWorkController:
    def __init__(self):
        self.reset_count = 0

    def reset(self):
        self.reset_count += 1


class FakeDataManager:
    def __init__(self, *, rows=None, export_result=None, export_error=None):
        self.current_processing_index = 7
        self.excel_data = rows or []
        self.export_result = export_result
        self.export_error = export_error
        self.export_calls = []

    def export_grid_to_excel_data(self, output_dir, input_file_path_str):
        self.export_calls.append((output_dir, input_file_path_str))
        if self.export_error is not None:
            raise self.export_error
        return self.export_result


class FakeMessageBox:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def showinfo(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))

    def showerror(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))


class FakeApp:
    def __init__(self, *, data_manager=None, report_manager=None):
        self.logger = FakeLogger()
        self.work_controller = FakeWorkController()
        self.data_manager = data_manager or FakeDataManager()
        self.ocr_workflow_manager = report_manager or SimpleNamespace(
            _current_run_report=None
        )
        self.runtime_states = []
        self.refresh_count = 0
        self.quick_save_count = 0
        self.finalize_count = 0

    def _ready_or_error_state(self):
        return RuntimeState.READY

    def _set_runtime_state(self, state):
        self.runtime_states.append(state)

    def refresh_grid_ui(self):
        self.refresh_count += 1

    def quick_save_settings(self):
        self.quick_save_count += 1

    def _finalize_processing_states(self):
        self.finalize_count += 1


class FakeReportManager:
    def __init__(self, report=None):
        self._current_run_report = report
        self.flush_count = 0

    def _flush_current_run_report(self):
        self.flush_count += 1


def test_complete_work_resets_state_refreshes_and_saves_without_dialog():
    app = FakeApp()

    completion_actions.complete_work(app, "summary")

    assert app.work_controller.reset_count == 1
    assert app.data_manager.current_processing_index == -1
    assert app.runtime_states == [RuntimeState.READY]
    assert app.refresh_count == 1
    assert app.quick_save_count == 1
    assert app.finalize_count == 0
    assert app.logger.messages == [
        "[_on_work_complete_ui_only] 함수 호출됨 (Main Thread)"
    ]


def test_stop_completion_finalizes_states_refreshes_and_shows_message(monkeypatch):
    app = FakeApp()
    box = FakeMessageBox()
    monkeypatch.setattr(completion_actions, "messagebox", box)

    completion_actions.complete_stopped_work(app)

    assert app.work_controller.reset_count == 1
    assert app.data_manager.current_processing_index == -1
    assert app.runtime_states == [RuntimeState.READY]
    assert app.finalize_count == 1
    assert app.refresh_count == 1
    assert app.quick_save_count == 0
    assert box.info_calls == [
        (("중단됨", "작업이 사용자에 의해 중단되었습니다."), {}),
    ]
    assert app.logger.messages == ["[_on_work_stopped] 함수 호출됨 (Main Thread)"]


def test_build_ocr_summary_uses_completed_rows_and_total_items():
    rows = [
        {"상태": "완료", "날짜": "2026/05/11", "금리": "3.500"},
        {"상태": "오류", "날짜": "2026/05/11", "금리": ""},
        {"상태": "완료", "날짜": "", "금리": ""},
    ]

    summary = completion_actions.build_ocr_summary(rows, total_items=5)

    assert (
        summary
        == """📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: 5개
        성공적으로 처리된 항목: 2개
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """
    )


def test_build_ocr_summary_handles_empty_rows():
    summary = completion_actions.build_ocr_summary([], total_items=0)

    assert (
        summary
        == """📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: 0개
        성공적으로 처리된 항목: 0개
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """
    )


def test_finalize_export_and_complete_records_report_resets_and_shows_success(tmp_path):
    output_workbook = tmp_path / "source_updated.xlsx"
    output_workbook.write_text("ok", encoding="utf-8")
    rows = [
        {
            "종목코드": "A001",
            "종목명": "Alpha",
            "날짜": "2026/05/11",
            "금리": "3.500",
            "상태": "완료",
        }
    ]
    report = {
        "rows": [
            {
                "index": 0,
                "timing_ms": {"row_total_ms": 1.25},
                "ocr_confidence": {"date": 0.9},
            }
        ],
        "summary": {"processed_count": 1, "total_items": 1, "stopped": False},
        "errors": [],
    }
    data_manager = FakeDataManager(rows=rows, export_result=output_workbook)
    report_manager = FakeReportManager(report)
    app = FakeApp(data_manager=data_manager, report_manager=report_manager)
    box = FakeMessageBox()
    clock_values = iter([10.0, 10.25])

    completion_actions.finalize_export_and_complete(
        app,
        str(tmp_path),
        str(tmp_path / "source.xlsx"),
        "done",
        showinfo=box.showinfo,
        showerror=box.showerror,
        clock=lambda: next(clock_values),
    )

    assert app.finalize_count == 1
    assert data_manager.export_calls == [(str(tmp_path), str(tmp_path / "source.xlsx"))]
    assert app.work_controller.reset_count == 1
    assert data_manager.current_processing_index == -1
    assert app.runtime_states == [RuntimeState.READY]
    assert app.refresh_count == 1
    assert report_manager.flush_count == 1
    assert report["rows"][0]["timing_ms"] == {"row_total_ms": 1.25}
    assert report["rows"][0]["ocr_confidence"] == {"date": 0.9}
    assert report["summary"]["export_timing_ms"] == {"export_ms": 250.0}
    assert report["summary"]["output_workbook_path"] == str(output_workbook)
    assert report["errors"] == []
    assert box.info_calls == [(("처리 완료", "done"), {})]
    assert box.error_calls == []


def test_finalize_export_and_complete_records_export_failure_and_skips_success(
    tmp_path,
):
    rows = [
        {"종목코드": "A001", "종목명": "Alpha", "날짜": "", "금리": "", "상태": "오류"}
    ]
    report = {
        "rows": [],
        "summary": {"processed_count": 0, "total_items": 1, "stopped": False},
        "errors": [],
    }
    data_manager = FakeDataManager(rows=rows, export_error=ValueError("bad workbook"))
    report_manager = FakeReportManager(report)
    app = FakeApp(data_manager=data_manager, report_manager=report_manager)
    box = FakeMessageBox()
    clock_values = iter([20.0, 20.001])

    completion_actions.finalize_export_and_complete(
        app,
        str(tmp_path),
        str(tmp_path / "source.xlsx"),
        "done",
        showinfo=box.showinfo,
        showerror=box.showerror,
        clock=lambda: next(clock_values),
    )

    assert app.work_controller.reset_count == 1
    assert app.refresh_count == 1
    assert report_manager.flush_count == 1
    assert report["errors"] == ["Excel export failed: bad workbook"]
    assert box.error_calls == [
        (("Excel export failed", "Excel export failed: bad workbook"), {})
    ]
    assert box.info_calls == []


def test_legacy_app_completion_methods_delegate(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "complete_work_action",
        lambda app_ref, summary: calls.append(("complete", app_ref, summary)),
    )
    monkeypatch.setattr(
        ocr_module,
        "complete_stopped_work_action",
        lambda app_ref: calls.append(("stopped", app_ref)),
    )

    app._on_work_complete_ui_only("summary")
    app._on_work_stopped()

    assert calls == [("complete", app, "summary"), ("stopped", app)]


def test_legacy_summary_methods_delegate(ocr_module, monkeypatch):
    rows = [{"상태": "완료"}]
    data_manager = SimpleNamespace(excel_data=rows)
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    app.data_manager = data_manager
    manager = ocr_module.OCRWorkflowManager.__new__(ocr_module.OCRWorkflowManager)
    manager.data_manager = data_manager
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "build_ocr_summary_action",
        lambda actual_rows, total: calls.append((actual_rows, total)) or "summary",
    )

    assert app._generate_ocr_summary_internal(99, 3) == "summary"
    assert manager._generate_ocr_summary_internal(99, 4) == "summary"
    assert calls == [(rows, 3), (rows, 4)]


def test_legacy_finalize_export_methods_delegate(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    manager = ocr_module.OCRWorkflowManager.__new__(ocr_module.OCRWorkflowManager)
    manager.app = app
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "finalize_export_and_complete_action",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    app._finalize_export_and_complete("out", "in.xlsx", "summary")
    manager._finalize_export_and_complete("out2", "in2.xlsx", "summary2")

    assert calls[0][0] == (app, "out", "in.xlsx", "summary")
    assert set(calls[0][1]) == {"showerror", "showinfo"}
    assert calls[1][0] == (app, "out2", "in2.xlsx", "summary2")
    assert calls[1][1]["report_manager"] is manager
    assert calls[1][1]["reset_work_state"] is False
    assert {"showerror", "showinfo"}.issubset(calls[1][1])


def test_legacy_manager_finalize_export_uses_app_and_manager_report(
    ocr_module,
    monkeypatch,
    tmp_path,
):
    output_workbook = tmp_path / "source_updated.xlsx"
    output_workbook.write_text("ok", encoding="utf-8")
    rows = [
        {
            "종목코드": "A001",
            "종목명": "Alpha",
            "날짜": "2026/05/11",
            "금리": "3.500",
            "상태": "완료",
        }
    ]
    data_manager = FakeDataManager(rows=rows, export_result=output_workbook)
    app = FakeApp(data_manager=data_manager)
    manager = ocr_module.OCRWorkflowManager.__new__(ocr_module.OCRWorkflowManager)
    manager.app = app
    manager._current_run_report = {
        "rows": [{"index": 0, "timing_ms": {"row_total_ms": 1.0}}],
        "summary": {"processed_count": 1, "total_items": 1, "stopped": False},
        "errors": [],
    }
    manager.flush_count = 0
    manager._flush_current_run_report = lambda: setattr(
        manager, "flush_count", manager.flush_count + 1
    )
    infos = []
    errors = []
    monkeypatch.setattr(
        ocr_module.messagebox,
        "showinfo",
        lambda *args, **kwargs: infos.append((args, kwargs)),
    )
    monkeypatch.setattr(
        ocr_module.messagebox,
        "showerror",
        lambda *args, **kwargs: errors.append((args, kwargs)),
    )

    manager._finalize_export_and_complete(
        str(tmp_path), str(tmp_path / "source.xlsx"), "done"
    )

    assert app.finalize_count == 1
    assert app.work_controller.reset_count == 0
    assert data_manager.current_processing_index == 7
    assert app.runtime_states == []
    assert app.refresh_count == 1
    assert manager.flush_count == 1
    assert manager._current_run_report["errors"] == []
    assert infos == [(("처리 완료", "done"), {})]
    assert errors == []
