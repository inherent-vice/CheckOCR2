"""Application lifecycle actions for the legacy Tk shell."""

from __future__ import annotations

from typing import Any


def quit_app(app: Any) -> None:
    if app.work_controller.is_running:
        app.logger.info("작업 진행 중, 종료 요청. 중단 처리 시도.")
        app.work_controller.stop_work()
        worker_thread = getattr(app, "worker_thread", None)
        if worker_thread and worker_thread.is_alive:
            try:
                worker_thread.join(timeout=2)
                if worker_thread.is_alive:
                    app.logger.warning(
                        "작업 스레드가 종료 시간 내에 응답하지 않았습니다."
                    )
            except (AttributeError, RuntimeError) as exc:
                app.logger.error(f"작업 스레드 종료 중 오류 발생: {exc}")

    app.destroy()
