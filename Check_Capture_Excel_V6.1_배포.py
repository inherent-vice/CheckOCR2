"""Compatibility launcher for the final V6.1 release filename.

The canonical application implementation now lives in ``check_capture_ocr.py``.
Keep this file so existing shortcuts and operator notes that launch the Korean
release filename continue to work.
"""

from check_capture_ocr import CheckCaptureOCRApp


def main():
    app = CheckCaptureOCRApp()
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    app.mainloop()


if __name__ == "__main__":
    main()
