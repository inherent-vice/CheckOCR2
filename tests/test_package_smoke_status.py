from __future__ import annotations

import json
from datetime import datetime

from checkocr2.package_smoke_status import (
    PACKAGE_SMOKE_FAST_OCR_ENV,
    build_package_smoke_status,
    package_smoke_fast_ocr_enabled,
    write_package_smoke_status,
)
from checkocr2.runtime_state import RuntimeState


def test_package_smoke_fast_ocr_enabled_reads_exact_env_flag():
    assert package_smoke_fast_ocr_enabled({PACKAGE_SMOKE_FAST_OCR_ENV: "1"}) is True
    assert package_smoke_fast_ocr_enabled({PACKAGE_SMOKE_FAST_OCR_ENV: "true"}) is False
    assert package_smoke_fast_ocr_enabled({}) is False


def test_build_package_smoke_status_uses_runtime_state_value(tmp_path):
    settings_file = tmp_path / "CheckOCR2" / "settings.json"

    payload = build_package_smoke_status(
        runtime_state=RuntimeState.READY,
        ocr_ready=True,
        settings_file=settings_file,
        now=lambda: datetime(2026, 5, 11, 16, 30, 0),
    )

    assert payload == {
        "runtime_state": "Ready",
        "ocr_ready": True,
        "settings_file": str(settings_file),
        "written_at": "2026-05-11T16:30:00",
    }


def test_write_package_smoke_status_creates_parent_and_writes_json(tmp_path):
    status_file = tmp_path / "nested" / "status.json"

    written_path = write_package_smoke_status(
        status_file,
        runtime_state=RuntimeState.OCR_LOADING,
        ocr_ready=False,
        settings_file=None,
        now=lambda: datetime(2026, 5, 11, 16, 31, 0),
    )

    assert written_path == status_file
    assert json.loads(status_file.read_text(encoding="utf-8")) == {
        "runtime_state": "OCR Loading",
        "ocr_ready": False,
        "settings_file": None,
        "written_at": "2026-05-11T16:31:00",
    }


def test_write_package_smoke_status_ignores_missing_status_path():
    assert (
        write_package_smoke_status(
            None,
            runtime_state=RuntimeState.READY,
            ocr_ready=True,
            settings_file=None,
        )
        is None
    )
