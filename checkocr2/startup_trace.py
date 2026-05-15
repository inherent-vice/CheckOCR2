"""Startup milestone tracing for source and packaged CheckOCR2 launches."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .packaged_paths import packaged_file_path
from .settings import APP_NAME

_PROCESS_STARTED_AT = time.perf_counter()
_SESSION_ID = uuid.uuid4().hex[:12]


def startup_trace_path(environ: Mapping[str, str] | None = None) -> Path:
    packaged_trace = packaged_file_path("startup_trace.jsonl")
    if packaged_trace is not None:
        return packaged_trace

    env = os.environ if environ is None else environ
    appdata = env.get("APPDATA")
    if appdata:
        base = Path(appdata) / APP_NAME
    else:
        base = Path.home() / ".checkocr2"
    return base / "logs" / "startup_trace.jsonl"


def record_startup_event(event: str, **details: Any) -> None:
    payload = {
        "session_id": _SESSION_ID,
        "event": event,
        "elapsed_ms": round((time.perf_counter() - _PROCESS_STARTED_AT) * 1000, 3),
        "pid": os.getpid(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "time": datetime.now(UTC).isoformat(),
    }
    payload.update({key: _jsonable(value) for key, value in details.items()})
    try:
        path = startup_trace_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            stream.write("\n")
    except OSError:
        return


def paddlex_cache_dir(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    return Path(env.get("PADDLE_PDX_CACHE_HOME") or (Path.home() / ".paddlex"))


def paddle_model_cache_state(
    model_names: Iterable[str],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    cache_root = paddlex_cache_dir(env) / "official_models"
    roots = [cache_root]
    configured_model_root = env.get("CHECKOCR2_PADDLE_MODEL_ROOT")
    if configured_model_root:
        roots.insert(0, Path(configured_model_root))
    models: dict[str, bool] = {}
    for model_name in model_names:
        models[str(model_name)] = any((root / str(model_name)).is_dir() for root in roots)
    return {
        "cache_dir": str(cache_root),
        "model_roots": [str(root) for root in roots],
        "all_present": all(models.values()) if models else False,
        "models": models,
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_jsonable(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
