"""Compatibility launcher for the CheckOCR2 Tk app."""

from __future__ import annotations

import sys

from checkocr2 import app as _app_module
from checkocr2.app import CheckCaptureOCRApp, main

__all__ = ["CheckCaptureOCRApp", "main"]

if __name__ == "__main__":
    raise SystemExit(main())

sys.modules[__name__] = _app_module
