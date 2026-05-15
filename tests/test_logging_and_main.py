from __future__ import annotations

import importlib
import logging
import queue
import sys
import threading
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace

import pytest

from checkocr2.logging_config import (
    TkinterLogHandler,
    default_log_path,
    default_session_log_path,
    install_global_exception_handlers,
    log_session_banner,
    reset_logging,
    setup_logging,
)


@pytest.fixture(autouse=True)
def _restore_logging_state():
    original_excepthook = sys.excepthook
    original_thread_excepthook = threading.excepthook
    try:
        yield
    finally:
        reset_logging()
        sys.excepthook = original_excepthook
        threading.excepthook = original_thread_excepthook


def _owned_root_handlers() -> list[logging.Handler]:
    return [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_checkocr2_owned", False)
    ]


class FakeTextWidget:
    def __init__(self, exists=True):
        self.exists = exists

    def winfo_exists(self):
        return self.exists


def test_tkinter_log_handler_forwards_log_display_event():
    events = queue.Queue()
    handler = TkinterLogHandler(FakeTextWidget(), events)

    handler.emit(logging.LogRecord("test", logging.WARNING, __file__, 1, "message", (), None))

    assert events.get_nowait()[0:2] == ("log_display", "WARNING")


def test_tkinter_log_handler_does_not_touch_widget_from_emit_thread():
    events = queue.Queue()

    class UnsafeWidget:
        def winfo_exists(self):
            raise RuntimeError("main thread is not in main loop")

    handler = TkinterLogHandler(UnsafeWidget(), events)

    handler.emit(logging.LogRecord("test", logging.INFO, __file__, 1, "threaded", (), None))

    assert events.get_nowait()[0:2] == ("log_display", "INFO")


def test_setup_logging_installs_owned_handlers_on_root(tmp_path):
    events = queue.Queue()
    log_path = tmp_path / "ocr_app.log"
    session_path = tmp_path / "sessions" / "session.log"

    logger = setup_logging(
        events, log_path=log_path, session_log_path=session_path
    )
    logger.info("hello")
    logger = setup_logging(
        events, log_path=log_path, session_log_path=session_path
    )

    owned = _owned_root_handlers()
    assert len(owned) == 3
    assert any(isinstance(handler, RotatingFileHandler) for handler in owned)
    assert log_path.exists()
    assert session_path.exists()
    assert logger.propagate is True


def test_setup_logging_defaults_to_rotating_appdata_log(tmp_path, monkeypatch):
    events = queue.Queue()
    appdata = tmp_path / "appdata"
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("APPDATA", str(appdata))

    logger = setup_logging(
        events, max_bytes=128, backup_count=2, enable_session_log=False
    )
    logger.info("hello")

    log_root = appdata / "CheckOCR2" / "logs"
    assert (log_root / "ocr_app.log").exists()
    assert not (cwd / "ocr_app.log").exists()
    rotating = [
        handler
        for handler in _owned_root_handlers()
        if isinstance(handler, RotatingFileHandler)
    ]
    assert rotating, "rotating file handler must be attached to the root logger"
    assert rotating[0].maxBytes == 128
    assert rotating[0].backupCount == 2


def test_default_log_paths_use_packaged_exe_directory(tmp_path, monkeypatch):
    exe_path = tmp_path / "CheckCaptureOCR_V7.0.exe"
    exe_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))

    assert default_log_path() == tmp_path / "ocr_app.log"
    assert default_session_log_path().parent == tmp_path / "sessions"


def test_setup_logging_captures_third_party_logger(tmp_path):
    events = queue.Queue()
    log_path = tmp_path / "ocr_app.log"

    setup_logging(events, log_path=log_path, enable_session_log=False)
    foreign = logging.getLogger("checkocr2.tests.third_party_capture")
    foreign.setLevel(logging.DEBUG)
    foreign.debug("third-party visibility")

    for handler in logging.getLogger().handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert "third-party visibility" in content
    assert "checkocr2.tests.third_party_capture" in content


def test_setup_logging_writes_session_file_with_rich_format(tmp_path):
    events = queue.Queue()
    log_path = tmp_path / "ocr_app.log"
    session_path = tmp_path / "sessions" / "specific.log"

    logger = setup_logging(
        events, log_path=log_path, session_log_path=session_path
    )
    logger.info("session hello")

    for handler in logging.getLogger().handlers:
        handler.flush()
    content = session_path.read_text(encoding="utf-8")
    assert "session hello" in content
    assert "INFO" in content
    assert "test_setup_logging_writes_session_file_with_rich_format" in content


def test_setup_logging_quiets_noisy_loggers(tmp_path):
    events = queue.Queue()
    log_path = tmp_path / "ocr_app.log"

    noisy = logging.getLogger("PIL")
    noisy.setLevel(logging.DEBUG)
    setup_logging(
        events,
        log_path=log_path,
        enable_session_log=False,
        quiet_loggers=("PIL",),
    )

    assert logging.getLogger("PIL").level == logging.WARNING


def test_setup_logging_install_exception_hooks_logs_uncaught_exception(tmp_path):
    events = queue.Queue()
    log_path = tmp_path / "ocr_app.log"

    setup_logging(
        events,
        log_path=log_path,
        enable_session_log=False,
        install_exception_hooks=True,
    )

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        sys.excepthook(*sys.exc_info())

    for handler in logging.getLogger().handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert "처리되지 않은 예외" in content
    assert "RuntimeError: boom" in content


def test_install_global_exception_handlers_records_thread_exception(tmp_path):
    events = queue.Queue()
    log_path = tmp_path / "ocr_app.log"

    setup_logging(events, log_path=log_path, enable_session_log=False)
    install_global_exception_handlers()

    args = SimpleNamespace(
        exc_type=RuntimeError,
        exc_value=RuntimeError("thread boom"),
        exc_traceback=None,
        thread=SimpleNamespace(name="worker-1"),
    )
    threading.excepthook(args)

    for handler in logging.getLogger().handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert "thread boom" in content
    assert "worker-1" in content


def test_log_session_banner_emits_version_and_paths(tmp_path, caplog):
    events = queue.Queue()
    log_path = tmp_path / "ocr_app.log"
    session_path = tmp_path / "sessions" / "banner.log"

    logger = setup_logging(
        events, log_path=log_path, session_log_path=session_path
    )

    with caplog.at_level(logging.INFO, logger="OCRApp"):
        log_session_banner(logger, extra={"테마": "modern_blue"})

    messages = "\n".join(record.message for record in caplog.records)
    assert "CheckOCR2 세션 시작" in messages
    assert "버전:" in messages
    assert "테마" in messages
    assert str(session_path) in messages


def test_package_main_constructs_app(monkeypatch):
    import checkocr2.app as app_module
    import checkocr2.main as main_module

    calls = []

    class FakeApp:
        def protocol(self, name, callback):
            calls.append(("protocol", name, callback))

        def quit_app(self):
            calls.append(("quit",))

        def mainloop(self):
            calls.append(("mainloop",))

    monkeypatch.setattr(app_module, "CheckCaptureOCRApp", FakeApp)

    main_module.main()

    assert calls[0][0:2] == ("protocol", "WM_DELETE_WINDOW")
    assert calls[-1] == ("mainloop",)
    assert main_module.main is app_module.main


def test_root_launcher_import_aliases_package_app():
    import checkocr2.app as app_module

    root_module = importlib.import_module("check_capture_ocr")

    assert root_module is app_module
    assert root_module.CheckCaptureOCRApp is app_module.CheckCaptureOCRApp
    assert root_module.CheckCaptureOCRApp.__module__ == "checkocr2.app"
