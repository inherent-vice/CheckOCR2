"""Compatibility launcher for the final V6.1 release filename.

The canonical application implementation now lives in ``check_capture_ocr.py``.
Keep this file so existing shortcuts and operator notes that launch the Korean
release filename continue to work.
"""

from checkocr2.main import main


if __name__ == "__main__":
    main()
