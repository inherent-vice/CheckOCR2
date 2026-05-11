"""Work completion actions for the legacy Tk shell."""

from __future__ import annotations

from tkinter import messagebox
from typing import Any


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
