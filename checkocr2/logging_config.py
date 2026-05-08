"""Logging helpers for the Tkinter application."""

from __future__ import annotations

import logging
from pathlib import Path
from queue import Queue
from typing import Any


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
        if not self.text_widget or not self.text_widget.winfo_exists():
            return
        self.message_queue.put(("log_display", record.levelname, self.format(record)))


def setup_logging(log_queue: Queue, *, log_path: str | Path = "ocr_app.log") -> logging.Logger:
    """Configure the application logger without duplicating handlers."""

    logger = logging.getLogger("OCRApp")
    logger.handlers = []
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
