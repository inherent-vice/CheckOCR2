"""PyInstaller runtime hook for packaged PaddleOCR native DLL discovery."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_DLL_DIRECTORY_HANDLES = []


def _add_dll_directory(path: Path) -> None:
    if not path.is_dir():
        return
    path_text = str(path)
    os.environ["PATH"] = path_text + os.pathsep + os.environ.get("PATH", "")
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if callable(add_dll_directory):
        _DLL_DIRECTORY_HANDLES.append(add_dll_directory(path_text))


def _runtime_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[1]


def _deploy_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _local_runtime_dir() -> Path:
    configured = os.environ.get("CHECKOCR2_LOCAL_PADDLE_RUNTIME_DIR")
    if configured:
        return Path(configured)
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "CheckOCR2" / "paddle_runtime"
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "CheckOCR2" / "paddle_runtime"
    return Path.home() / ".checkocr2" / "paddle_runtime"


def _mirror_bundled_models(source_root: Path, target_root: Path) -> Path:
    target_root.mkdir(parents=True, exist_ok=True)
    for source_model in source_root.iterdir():
        if not source_model.is_dir():
            continue
        target_model = target_root / source_model.name
        sentinel = target_model / ".checkocr2_model_ready"
        if sentinel.exists():
            continue
        if target_model.exists():
            shutil.rmtree(target_model)
        shutil.copytree(source_model, target_model)
        sentinel.write_text("ready\n", encoding="utf-8")
    return target_root


root = _runtime_root()
deploy_dir = _deploy_dir()
local_runtime_dir = _local_runtime_dir()
runtime_cache_dir = local_runtime_dir / "paddle_cache"
bundled_model_root = root / "checkocr2" / "paddle_models"
if bundled_model_root.is_dir():
    os.environ.setdefault("CHECKOCR2_BUNDLED_PADDLE_MODEL_ROOT", str(bundled_model_root))
    runtime_model_root = bundled_model_root
    try:
        runtime_model_root = _mirror_bundled_models(
            bundled_model_root,
            local_runtime_dir / "paddle_models",
        )
        os.environ.setdefault("CHECKOCR2_PADDLE_MODEL_MIRROR_STATUS", "ready")
    except Exception as exc:
        os.environ.setdefault("CHECKOCR2_PADDLE_MODEL_MIRROR_STATUS", "fallback")
        os.environ.setdefault("CHECKOCR2_PADDLE_MODEL_MIRROR_ERROR", str(exc))
    os.environ.setdefault("CHECKOCR2_PADDLE_MODEL_ROOT", str(runtime_model_root))
os.environ.setdefault("CHECKOCR2_DEPLOY_DIR", str(deploy_dir))
try:
    runtime_cache_dir.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    os.environ.setdefault("CHECKOCR2_PADDLE_CACHE_ERROR", str(exc))
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(runtime_cache_dir))
os.environ.setdefault("PADDLE_HOME", str(runtime_cache_dir))
os.environ.setdefault("PADDLEOCR_HOME", str(runtime_cache_dir))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
for candidate in (
    root / "paddle" / "base",
    root / "paddle" / "libs",
    root / "paddle" / "base" / "lib",
    root / "_internal" / "paddle" / "base",
    root / "_internal" / "paddle" / "libs",
    root / "_internal" / "paddle" / "base" / "lib",
):
    _add_dll_directory(candidate)
