from __future__ import annotations

from checkocr2.runtime_state import RuntimeState, runtime_state_ui


def test_runtime_state_ui_mapping_is_explicit():
    assert runtime_state_ui(RuntimeState.STARTING).run_button_text == "OCR 준비 중..."
    assert runtime_state_ui(RuntimeState.OCR_LOADING).run_button_state == "disabled"
    assert runtime_state_ui(RuntimeState.READY).run_button_text == "🚀 OCR 시작 (F5)"
    assert runtime_state_ui(RuntimeState.RUNNING).stop_button_state == "normal"
    assert runtime_state_ui(RuntimeState.STOPPING).run_button_text == "중단 중..."
    assert runtime_state_ui(RuntimeState.ERROR).run_button_text == "OCR 초기화 실패"
