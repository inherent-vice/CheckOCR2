"""Path helpers for source and PyInstaller-packaged runs."""

from __future__ import annotations

import sys
from pathlib import Path


def packaged_app_dir() -> Path | None:
    """Return the directory containing the packaged EXE, or ``None`` in source runs."""

    if not bool(getattr(sys, "frozen", False)):
        return None
    return Path(sys.executable).resolve().parent


def packaged_file_path(filename: str) -> Path | None:
    app_dir = packaged_app_dir()
    if app_dir is None:
        return None
    return app_dir / filename
