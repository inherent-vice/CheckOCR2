"""Application bootstrap for package-based launchers."""

from __future__ import annotations

from .app import CheckCaptureOCRApp


def main() -> None:
    app = CheckCaptureOCRApp()
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    app.mainloop()


if __name__ == "__main__":
    main()
