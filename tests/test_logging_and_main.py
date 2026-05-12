from __future__ import annotations

import importlib
import logging
import queue

from checkocr2.logging_config import TkinterLogHandler, setup_logging


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


def test_setup_logging_replaces_handlers(tmp_path):
    events = queue.Queue()
    log_path = tmp_path / "ocr_app.log"

    logger = setup_logging(events, log_path=log_path)
    logger.info("hello")
    logger = setup_logging(events, log_path=log_path)

    assert len(logger.handlers) == 2
    assert log_path.exists()


def test_setup_logging_defaults_to_rotating_appdata_log(tmp_path, monkeypatch):
    events = queue.Queue()
    appdata = tmp_path / "appdata"
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("APPDATA", str(appdata))

    logger = setup_logging(events, max_bytes=128, backup_count=2)
    logger.info("hello")

    assert (appdata / "CheckOCR2" / "logs" / "ocr_app.log").exists()
    assert not (cwd / "ocr_app.log").exists()
    assert logger.handlers[0].maxBytes == 128
    assert logger.handlers[0].backupCount == 2


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
