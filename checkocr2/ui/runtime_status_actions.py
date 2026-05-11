"""Runtime-state and package-smoke status actions for the legacy Tk shell."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from checkocr2.package_smoke_status import (
    PACKAGE_SMOKE_STATUS_FILE_ENV,
    write_package_smoke_status,
)
from checkocr2.runtime_state import RuntimeState, runtime_state_ui


def set_runtime_state(app: Any, state: RuntimeState) -> None:
    app.runtime_state = state
    ui_state = runtime_state_ui(state)
    if not hasattr(app, "run_btn") or not app.run_btn:
        write_package_smoke_status_for_app(app)
        return
    app.run_btn.config(state=ui_state.run_button_state, text=ui_state.run_button_text)
    if hasattr(app, "stop_btn") and app.stop_btn:
        app.stop_btn.config(state=ui_state.stop_button_state)
    write_package_smoke_status_for_app(app)


def set_ocr_ready_ui(app: Any, ready: bool) -> None:
    app._set_runtime_state(RuntimeState.READY if ready else RuntimeState.OCR_LOADING)


def ready_or_error_state(app: Any) -> RuntimeState:
    return RuntimeState.READY if app.ocr_workflow_manager.ocr_reader else RuntimeState.ERROR


def write_package_smoke_status_for_app(
    app: Any,
    *,
    environ: Mapping[str, str] | None = None,
) -> None:
    env = os.environ if environ is None else environ
    status_file = env.get(PACKAGE_SMOKE_STATUS_FILE_ENV)
    if not status_file:
        return None

    try:
        write_package_smoke_status(
            status_file,
            runtime_state=app.runtime_state,
            ocr_ready=bool(app.ocr_workflow_manager.ocr_reader),
            settings_file=getattr(
                getattr(app, "settings_manager", None),
                "settings_file",
                None,
            ),
        )
    except OSError as exc:
        if hasattr(app, "logger"):
            app.logger.debug("Package smoke status write failed: %s", exc)
    return None
