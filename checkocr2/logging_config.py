"""Logging helpers for the Tkinter application.

Centralised configuration that:

* Routes every log emitted in the process (CheckOCR2 modules **and**
  third-party libraries such as PaddleOCR, EasyOCR, Pillow) to a rotating
  long-term file plus a per-session timestamped file.
* Captures uncaught exceptions from the main thread *and* worker threads,
  so even crashes are persisted on disk.
* Records a startup banner so log files are self-describing.

The function ``setup_logging`` remains backwards compatible — callers still
receive the ``OCRApp`` logger — but the heavy lifting (file handlers,
stream handler, session log) is now attached to the **root** logger so that
records from any library propagate into the same file.
"""

from __future__ import annotations

import datetime
import logging
import os
import platform
import sys
import threading
from collections.abc import Iterable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from queue import Queue
from typing import Any

DEFAULT_LOG_FILENAME = "ocr_app.log"
DEFAULT_SESSION_LOG_DIRNAME = "sessions"
DEFAULT_SESSION_LOG_FILENAME_FMT = "session_{timestamp}.log"
DEFAULT_MAX_LOG_BYTES = 5_000_000
DEFAULT_LOG_BACKUP_COUNT = 5

UI_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
UI_LOG_DATEFMT = "%H:%M:%S"

FILE_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(threadName)s | "
    "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
)
FILE_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

NOISY_LOGGERS_AT_WARNING: tuple[str, ...] = (
    "PIL",
    "PIL.PngImagePlugin",
    "PIL.TiffImagePlugin",
    "urllib3",
    "matplotlib",
    "fontTools",
    "asyncio",
    "paddle",
    "paddleocr",
    "ppocr",
    "easyocr",
)

_OWNED_TAG = "_checkocr2_owned"

_LAST_LOG_PATH: Path | None = None
_LAST_SESSION_LOG_PATH: Path | None = None


def default_log_path() -> Path:
    """Return the per-user application log path (rotating)."""

    from .settings import user_settings_path

    return user_settings_path().parent / "logs" / DEFAULT_LOG_FILENAME


def default_session_log_path(timestamp: datetime.datetime | None = None) -> Path:
    """Return a per-session log file path with a timestamped filename."""

    ts = (timestamp or datetime.datetime.now()).strftime("%Y%m%d_%H%M%S")
    base = default_log_path().parent / DEFAULT_SESSION_LOG_DIRNAME
    return base / DEFAULT_SESSION_LOG_FILENAME_FMT.format(timestamp=ts)


def last_log_paths() -> tuple[Path | None, Path | None]:
    """Return ``(rotating_path, session_path)`` from the most recent setup."""

    return _LAST_LOG_PATH, _LAST_SESSION_LOG_PATH


class TkinterLogHandler(logging.Handler):
    """Forward formatted log messages to the Tk queue for UI display."""

    def __init__(self, text_widget: Any, message_queue: Queue):
        super().__init__()
        self.text_widget = text_widget
        self.message_queue = message_queue
        self.formatter = logging.Formatter(UI_LOG_FORMAT, datefmt=UI_LOG_DATEFMT)

    def emit(self, record: logging.LogRecord) -> None:
        if not self.text_widget:
            return
        self.message_queue.put(("log_display", record.levelname, self.format(record)))


def _mark_owned(handler: logging.Handler) -> logging.Handler:
    setattr(handler, _OWNED_TAG, True)
    return handler


def _remove_owned_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, _OWNED_TAG, False):
            try:
                handler.close()
            except Exception:
                pass
            logger.removeHandler(handler)


def reset_logging() -> None:
    """Detach and close handlers installed by :func:`setup_logging`.

    Primarily intended for tests that want a clean slate.
    """

    global _LAST_LOG_PATH, _LAST_SESSION_LOG_PATH
    _remove_owned_handlers(logging.getLogger())
    _remove_owned_handlers(logging.getLogger("OCRApp"))
    _LAST_LOG_PATH = None
    _LAST_SESSION_LOG_PATH = None


def setup_logging(
    log_queue: Queue,
    *,
    log_path: str | Path | None = None,
    session_log_path: str | Path | None = None,
    max_bytes: int = DEFAULT_MAX_LOG_BYTES,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
    level: int = logging.DEBUG,
    stream_level: int = logging.INFO,
    enable_session_log: bool = True,
    capture_warnings: bool = True,
    install_exception_hooks: bool = False,
    quiet_loggers: Iterable[str] | None = NOISY_LOGGERS_AT_WARNING,
) -> logging.Logger:
    """Configure root + ``OCRApp`` loggers and return ``OCRApp``.

    The function is idempotent: each call removes handlers previously
    installed by this module before re-attaching new ones, so embedding
    applications and the test suite can safely call it multiple times.
    """

    global _LAST_LOG_PATH, _LAST_SESSION_LOG_PATH

    file_formatter = logging.Formatter(FILE_LOG_FORMAT, datefmt=FILE_LOG_DATEFMT)
    stream_formatter = logging.Formatter(UI_LOG_FORMAT, datefmt=FILE_LOG_DATEFMT)

    root_logger = logging.getLogger()
    _remove_owned_handlers(root_logger)
    root_logger.setLevel(level)

    resolved_log_path = Path(log_path) if log_path is not None else default_log_path()
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        resolved_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)
    root_logger.addHandler(_mark_owned(file_handler))
    _LAST_LOG_PATH = resolved_log_path

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_formatter)
    stream_handler.setLevel(stream_level)
    root_logger.addHandler(_mark_owned(stream_handler))

    if enable_session_log:
        resolved_session_path = (
            Path(session_log_path)
            if session_log_path is not None
            else default_session_log_path()
        )
        resolved_session_path.parent.mkdir(parents=True, exist_ok=True)
        session_handler = logging.FileHandler(resolved_session_path, encoding="utf-8")
        session_handler.setFormatter(file_formatter)
        session_handler.setLevel(level)
        root_logger.addHandler(_mark_owned(session_handler))
        _LAST_SESSION_LOG_PATH = resolved_session_path
    else:
        _LAST_SESSION_LOG_PATH = None

    for name in quiet_loggers or ():
        noisy = logging.getLogger(name)
        if noisy.level == logging.NOTSET or noisy.level < logging.WARNING:
            noisy.setLevel(logging.WARNING)

    logger = logging.getLogger("OCRApp")
    _remove_owned_handlers(logger)
    logger.setLevel(level)
    logger.propagate = True

    if capture_warnings:
        logging.captureWarnings(True)

    if install_exception_hooks:
        install_global_exception_handlers(logger)

    return logger


def install_global_exception_handlers(
    logger: logging.Logger | None = None,
) -> None:
    """Install ``sys.excepthook`` and ``threading.excepthook`` for crash logs."""

    bound = logger or logging.getLogger("OCRApp")

    def _excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        bound.critical(
            "처리되지 않은 예외 (메인 스레드)",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    def _thread_excepthook(args):
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        thread_name = args.thread.name if args.thread else "<unknown>"
        bound.critical(
            f"처리되지 않은 예외 (스레드 {thread_name})",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook


def log_session_banner(
    logger: logging.Logger | None = None,
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write a banner describing the current session to the log file."""

    bound = logger or logging.getLogger("OCRApp")

    try:
        from . import __display_version__, __version__
    except Exception:
        __display_version__ = "unknown"
        __version__ = "unknown"

    rotating_path, session_path = last_log_paths()

    bound.info("=" * 72)
    bound.info("CheckOCR2 세션 시작")
    bound.info("버전: %s (%s)", __display_version__, __version__)
    bound.info(
        "Python: %s | 플랫폼: %s",
        platform.python_version(),
        platform.platform(),
    )
    bound.info("실행 파일: %s", sys.executable)
    bound.info("작업 디렉터리: %s", os.getcwd())
    bound.info("PID: %s", os.getpid())
    if rotating_path:
        bound.info("로테이션 로그: %s", rotating_path)
    if session_path:
        bound.info("세션 로그: %s", session_path)
    if extra:
        for key, value in extra.items():
            bound.info("%s: %s", key, value)
    bound.info("=" * 72)
