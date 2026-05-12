from __future__ import annotations

from checkocr2.ui import lifecycle_actions


class FakeLogger:
    def __init__(self):
        self.info_messages = []
        self.warning_messages = []
        self.error_messages = []

    def info(self, message):
        self.info_messages.append(message)

    def warning(self, message):
        self.warning_messages.append(message)

    def error(self, message):
        self.error_messages.append(message)


class FakeWorkController:
    def __init__(self, *, is_running):
        self.is_running = is_running
        self.stop_count = 0

    def stop_work(self):
        self.stop_count += 1


class FakeWorkerThread:
    def __init__(self, *, alive_after_join=False, join_error=None):
        self.is_alive = True
        self.alive_after_join = alive_after_join
        self.join_error = join_error
        self.join_calls = []

    def join(self, timeout=None):
        self.join_calls.append(timeout)
        if self.join_error is not None:
            raise self.join_error
        self.is_alive = self.alive_after_join


class FakeApp:
    def __init__(self, *, is_running=False, worker_thread=None):
        self.logger = FakeLogger()
        self.work_controller = FakeWorkController(is_running=is_running)
        self.worker_thread = worker_thread
        self.destroy_count = 0

    def destroy(self):
        self.destroy_count += 1


def test_quit_app_destroys_without_stop_when_idle():
    app = FakeApp(is_running=False)

    lifecycle_actions.quit_app(app)

    assert app.work_controller.stop_count == 0
    assert app.destroy_count == 1
    assert app.logger.info_messages == []


def test_quit_app_stops_joins_worker_and_destroys_when_running():
    worker = FakeWorkerThread(alive_after_join=False)
    app = FakeApp(is_running=True, worker_thread=worker)

    lifecycle_actions.quit_app(app)

    assert app.work_controller.stop_count == 1
    assert worker.join_calls == [2]
    assert app.destroy_count == 1
    assert app.logger.warning_messages == []


def test_quit_app_warns_when_worker_remains_alive():
    worker = FakeWorkerThread(alive_after_join=True)
    app = FakeApp(is_running=True, worker_thread=worker)

    lifecycle_actions.quit_app(app)

    assert app.work_controller.stop_count == 1
    assert worker.join_calls == [2]
    assert app.destroy_count == 1
    assert app.logger.warning_messages == [
        "작업 스레드가 종료 시간 내에 응답하지 않았습니다."
    ]


def test_quit_app_logs_join_errors_and_still_destroys():
    worker = FakeWorkerThread(join_error=RuntimeError("boom"))
    app = FakeApp(is_running=True, worker_thread=worker)

    lifecycle_actions.quit_app(app)

    assert app.work_controller.stop_count == 1
    assert app.destroy_count == 1
    assert app.logger.error_messages == ["작업 스레드 종료 중 오류 발생: boom"]


def test_legacy_quit_app_delegates(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "quit_app_action",
        lambda app_ref: calls.append(app_ref),
    )

    app.quit_app()

    assert calls == [app]
