"""Runtime state model for the CheckOCR2 Tk shell."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RuntimeState(StrEnum):
    STARTING = "Starting"
    OCR_LOADING = "OCR Loading"
    READY = "Ready"
    RUNNING = "Running"
    STOPPING = "Stopping"
    ERROR = "Error"


@dataclass(frozen=True)
class RuntimeStateUi:
    run_button_state: str
    run_button_text: str
    stop_button_state: str


_UI_BY_STATE = {
    RuntimeState.STARTING: RuntimeStateUi("disabled", "OCR 준비 중...", "disabled"),
    RuntimeState.OCR_LOADING: RuntimeStateUi("disabled", "OCR 준비 중...", "disabled"),
    RuntimeState.READY: RuntimeStateUi("normal", "🚀 OCR 시작 (F5)", "disabled"),
    RuntimeState.RUNNING: RuntimeStateUi("normal", "⏹️ 중단 (F5)", "normal"),
    RuntimeState.STOPPING: RuntimeStateUi("disabled", "중단 중...", "disabled"),
    RuntimeState.ERROR: RuntimeStateUi("disabled", "OCR 초기화 실패", "disabled"),
}


def runtime_state_ui(state: RuntimeState) -> RuntimeStateUi:
    return _UI_BY_STATE[state]
