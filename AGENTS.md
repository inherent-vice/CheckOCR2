# Repository Guidelines

## Project Structure & Module Organization

CheckOCR2 is a Python/Tkinter desktop OCR tool for screen capture, EasyOCR processing, and Excel import/export. `check_capture_ocr.py` is the canonical app implementation and is the source used by PyInstaller. `Check_Capture_Excel_V6.1_배포.py` is a compatibility launcher for the previous final release filename. Historical V4/V5/V6 variants are preserved under `legacy/`; icon-generation utilities live under `tools/`. `docs/` contains project overview and improvement notes. Icon assets remain at the repository root as `app_icon*` and `eye_ocr_*` files.

## Build, Test, and Development Commands

- `python -m venv .venv` then `.venv\Scripts\Activate.ps1`: create and enter a local Windows virtual environment.
- `python -m pip install -r requirements.txt`: install GUI, OCR, Excel, image, and packaging dependencies.
- `python check_capture_ocr.py`: run the desktop app locally.
- `python Check_Capture_Excel_V6.1_배포.py`: run through the legacy final-release filename.
- `python -m compileall check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py`: quick syntax check before committing.
- `python -m PyInstaller build_app.spec`: build the OneDIR Windows package under `dist/CheckCaptureOCR_V6.1/`.

## Coding Style & Naming Conventions

Use Python 3 with 4-space indentation. Match the existing Tkinter class/method style and keep UI updates on the main thread through queues or callbacks. Prefer clear English identifiers for new code; preserve existing Korean UI text and comments when editing nearby behavior. Keep changes surgical because the main file is large and versioned copies are present.

## Testing Guidelines

There is no automated test suite yet. For code changes, at minimum run `compileall` and manually launch the app. Smoke-check the affected workflow: settings load/save, capture-area selection, OCR execution, Excel import/export, and package startup when build behavior changes. If adding tests, place them under `tests/` and use `test_*.py` names.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit prefixes such as `feat:` and `docs:`. Keep commits focused and avoid staging generated `build/`, `dist/`, `ocr_app.log`, or personal settings changes unless intentionally updating release artifacts. Pull requests should describe the user-visible change, list verification commands, note manual OCR/Excel checks, and include screenshots for UI changes.

## Security & Configuration Tips

Keep OCR and Excel processing local. Do not commit production spreadsheets, screenshots with sensitive financial data, API keys, or machine-specific paths. Treat `settings.json` changes carefully because it stores capture coordinates, presets, and runtime preferences.
