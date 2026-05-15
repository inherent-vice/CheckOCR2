from __future__ import annotations

import json
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


def test_paddle_model_cache_state_reports_official_model_presence(tmp_path):
    model_root = tmp_path / "official_models" / "korean_PP-OCRv5_mobile_rec"
    model_root.mkdir(parents=True)

    state = paddle_model_cache_state(
        ["korean_PP-OCRv5_mobile_rec", "missing_model"],
        environ={"PADDLE_PDX_CACHE_HOME": str(tmp_path)},
    )

    assert state == {
        "cache_dir": str(tmp_path / "official_models"),
        "all_present": False,
        "models": {
            "korean_PP-OCRv5_mobile_rec": True,
            "missing_model": False,
        },
    }
