"""Work completion actions for the legacy Tk shell."""

from __future__ import annotations

from tkinter import messagebox
from typing import Any


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
