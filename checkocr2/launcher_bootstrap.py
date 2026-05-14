"""Helpers for launching the app from the repository checkout."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_repo_venv() -> None:
    if getattr(sys, "frozen", False):
        return

    repo_root = Path(__file__).resolve().parents[1]
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        return

    current_executable = Path(sys.executable).resolve()
    if current_executable == venv_python.resolve():
        return

    os.execv(str(venv_python), [str(venv_python), *sys.argv])
