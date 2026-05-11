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
    def __init__(self):
        self.current_processing_index = 7


class FakeMessageBox:
    def __init__(self):
        self.info_calls = []

    def showinfo(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))


class FakeApp:
    def __init__(self):
        self.logger = FakeLogger()
        self.work_controller = FakeWorkController()
        self.data_manager = FakeDataManager()
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


def test_complete_work_resets_state_refreshes_and_saves_without_dialog():
    app = FakeApp()

    completion_actions.complete_work(app, "summary")

    assert app.work_controller.reset_count == 1
    assert app.data_manager.current_processing_index == -1
    assert app.runtime_states == [RuntimeState.READY]
    assert app.refresh_count == 1
    assert app.quick_save_count == 1
    assert app.finalize_count == 0
    assert app.logger.messages == ["[_on_work_complete_ui_only] 함수 호출됨 (Main Thread)"]


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

    assert summary == """📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: 5개
        성공적으로 처리된 항목: 2개
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """


def test_build_ocr_summary_handles_empty_rows():
    summary = completion_actions.build_ocr_summary([], total_items=0)

    assert summary == """📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: 0개
        성공적으로 처리된 항목: 0개
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """


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
