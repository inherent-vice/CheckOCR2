from __future__ import annotations

import json
import sys
from pathlib import Path

from checkocr2.startup_trace import (
    paddle_model_cache_state,
    record_startup_event,
    startup_trace_path,
)


def test_record_startup_event_writes_jsonl_under_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    record_startup_event("ocr_init_requested", trace_detail=Path("sample.txt"))

    trace_file = startup_trace_path()
    payload = json.loads(trace_file.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["event"] == "ocr_init_requested"
    assert payload["trace_detail"] == "sample.txt"
    assert payload["elapsed_ms"] >= 0
    assert payload["session_id"]


def test_startup_trace_path_uses_packaged_exe_directory(tmp_path, monkeypatch):
    exe_path = tmp_path / "CheckCaptureOCR_V7.0.exe"
    exe_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))

    assert startup_trace_path() == tmp_path / "startup_trace.jsonl"


def test_paddle_model_cache_state_reports_official_model_presence(tmp_path):
    model_root = tmp_path / "official_models" / "korean_PP-OCRv5_mobile_rec"
    model_root.mkdir(parents=True)

    state = paddle_model_cache_state(
        ["korean_PP-OCRv5_mobile_rec", "missing_model"],
        environ={"PADDLE_PDX_CACHE_HOME": str(tmp_path)},
    )

    assert state == {
        "cache_dir": str(tmp_path / "official_models"),
        "model_roots": [str(tmp_path / "official_models")],
        "all_present": False,
        "models": {
            "korean_PP-OCRv5_mobile_rec": True,
            "missing_model": False,
        },
    }


def test_paddle_model_cache_state_reports_configured_model_root(tmp_path):
    model_root = tmp_path / "paddle_models"
    (model_root / "korean_PP-OCRv5_mobile_rec").mkdir(parents=True)

    state = paddle_model_cache_state(
        ["korean_PP-OCRv5_mobile_rec"],
        environ={
            "PADDLE_PDX_CACHE_HOME": str(tmp_path / "cache"),
            "CHECKOCR2_PADDLE_MODEL_ROOT": str(model_root),
        },
    )

    assert state["all_present"] is True
    assert state["model_roots"] == [
        str(model_root),
        str(tmp_path / "cache" / "official_models"),
    ]
    assert state["models"] == {"korean_PP-OCRv5_mobile_rec": True}
