"""Logging helpers for the Tkinter application."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from queue import Queue
from typing import Any

DEFAULT_LOG_FILENAME = "ocr_app.log"
DEFAULT_MAX_LOG_BYTES = 1_000_000
DEFAULT_LOG_BACKUP_COUNT = 3


def default_log_path() -> Path:
    """Return the per-user application log path."""

    from .settings import user_settings_path

    return user_settings_path().parent / "logs" / DEFAULT_LOG_FILENAME


class TkinterLogHandler(logging.Handler):
    """Forward formatted log messages to the Tk queue."""

    def __init__(self, text_widget: Any, message_queue: Queue):
        super().__init__()
        self.text_widget = text_widget
        self.message_queue = message_queue
        self.formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )

    def emit(self, record: logging.LogRecord) -> None:
        if not self.text_widget:
            return
        self.message_queue.put(("log_display", record.levelname, self.format(record)))


def setup_logging(
    log_queue: Queue,
    *,
    log_path: str | Path | None = None,
    max_bytes: int = DEFAULT_MAX_LOG_BYTES,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> logging.Logger:
    """Configure the application logger without duplicating handlers."""

    logger = logging.getLogger("OCRApp")
    logger.handlers = []
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    resolved_log_path = Path(log_path) if log_path is not None else default_log_path()
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        resolved_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
