"""Package-smoke status helpers used by the Tk shell."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

PACKAGE_SMOKE_FAST_OCR_ENV = "CHECKOCR2_PACKAGE_SMOKE_FAST_OCR"
PACKAGE_SMOKE_STATUS_FILE_ENV = "CHECKOCR2_PACKAGE_SMOKE_STATUS_FILE"


def package_smoke_fast_ocr_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    env = os.environ if environ is None else environ
    return env.get(PACKAGE_SMOKE_FAST_OCR_ENV) == "1"


def build_package_smoke_status(
    *,
    runtime_state: Any,
    ocr_ready: bool,
    settings_file: str | os.PathLike[str] | None,
    now: Callable[[], datetime] = datetime.now,
) -> dict[str, Any]:
    return {
        "runtime_state": getattr(runtime_state, "value", runtime_state),
        "ocr_ready": bool(ocr_ready),
        "settings_file": str(settings_file) if settings_file is not None else None,
        "written_at": now().isoformat(),
    }


def write_package_smoke_status(
    status_file: str | os.PathLike[str] | None,
    *,
    runtime_state: Any,
    ocr_ready: bool,
    settings_file: str | os.PathLike[str] | None,
    now: Callable[[], datetime] = datetime.now,
) -> Path | None:
    if not status_file:
        return None

    path = Path(status_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_package_smoke_status(
        runtime_state=runtime_state,
        ocr_ready=ocr_ready,
        settings_file=settings_file,
        now=now,
    )
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    return path
