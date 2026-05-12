"""OCR initialization action helpers for the legacy Tk shell."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, Protocol

from checkocr2.package_smoke_status import package_smoke_fast_ocr_enabled
from checkocr2.runtime_state import RuntimeState


class ThreadLike(Protocol):
    def start(self) -> None: ...


ThreadFactory = Callable[..., ThreadLike]
FastOcrEnabled = Callable[[], bool]


def start_ocr_initialization(
    app: Any,
    *,
    thread_factory: ThreadFactory | None = None,
    fast_ocr_enabled: FastOcrEnabled = package_smoke_fast_ocr_enabled,
) -> None:
    if app.ocr_initializing or app.ocr_workflow_manager.ocr_reader:
        return

    app.ocr_initializing = True
    app._set_runtime_state(RuntimeState.OCR_LOADING)

    if fast_ocr_enabled():
        app.ocr_workflow_manager.ocr_reader = object()
        app.message_queue.put(("ocr_ready", True))
        return

    def initialize() -> None:
        app.ocr_workflow_manager.initialize_ocr()
        app.message_queue.put(("ocr_ready", app.ocr_workflow_manager.ocr_reader is not None))

    factory = thread_factory or threading.Thread
    app.ocr_init_thread = factory(target=initialize, daemon=True)
    app.ocr_init_thread.start()
