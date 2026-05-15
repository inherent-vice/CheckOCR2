"""Compatibility launcher for the CheckOCR2 Tk app."""

from __future__ import annotations

import sys

from checkocr2.launcher_bootstrap import ensure_repo_venv

ensure_repo_venv()

from checkocr2 import app as _app_module  # noqa: E402
from checkocr2.app import CheckCaptureOCRApp, main  # noqa: E402

__all__ = ["CheckCaptureOCRApp", "main"]

if __name__ == "__main__":
    raise SystemExit(main())

sys.modules[__name__] = _app_module
