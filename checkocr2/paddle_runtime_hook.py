"""PyInstaller runtime hook for packaged PaddleOCR native DLL discovery."""

from __future__ import annotations

import os
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


root = _runtime_root()
bundled_model_root = root / "checkocr2" / "paddle_models"
if bundled_model_root.is_dir():
    os.environ.setdefault("CHECKOCR2_PADDLE_MODEL_ROOT", str(bundled_model_root))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
for candidate in (
    root / "paddle" / "base",
    root / "paddle" / "libs",
    root / "_internal" / "paddle" / "base",
    root / "_internal" / "paddle" / "libs",
):
    _add_dll_directory(candidate)
