# Repository Guidelines

## Project Structure & Module Organization

CheckOCR2 is a Python/Tkinter desktop OCR tool for screen capture, EasyOCR processing, and Excel import/export. `check_capture_ocr.py` is the canonical GUI app and PyInstaller source; `Check_Capture_Excel_V6.1_배포.py` is the compatibility launcher. Reusable logic is being extracted under `checkocr2/` (`settings.py`, `excel_io.py`, `table_model.py`, `ocr_text.py`, `ocr_engine.py`, `screen_automation.py`). Tests live under `tests/`, benchmark tooling under `scripts/`, historical variants under `legacy/`, and icon utilities under `tools/`.

## Build, Test, and Development Commands

- `python -m venv .venv` then `.venv\Scripts\Activate.ps1`: create and enter a local Windows virtual environment.
- `python -m pip install -r requirements.txt`: install GUI, OCR, Excel, image, and packaging dependencies.
- `python check_capture_ocr.py`: run the desktop app locally.
- `python Check_Capture_Excel_V6.1_배포.py`: run through the legacy final-release filename.
- `python -m pytest --basetemp $env:TEMP\checkocr2-pytest`: run the automated test suite without Windows temp cleanup noise.
- `python -m ruff check .`: lint new package, scripts, tests, and the legacy app with scoped ignores.
- `python -m compileall check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py`: quick syntax check before committing.
- `python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture`: validate the OCR benchmark harness while fixtures are being built.
- `python -m PyInstaller build_app.spec`: build the OneDIR Windows package under `dist/CheckCaptureOCR_V6.1/`.

## Coding Style & Naming Conventions

Use Python 3.12 with 4-space indentation. Match the existing Tkinter style in `check_capture_ocr.py`; keep UI updates on the main thread through queues or callbacks. New reusable code should go in focused `checkocr2/` modules with typed helpers and pytest coverage. Preserve existing Korean UI text and operator behavior.

## Testing Guidelines

Use pytest for characterization and unit tests. Keep tests under `tests/` with `test_*.py` names; desktop automation, Tk, and EasyOCR should be stubbed unless doing an explicit live smoke. Cover settings migration, path handling, Excel import/export, OCR text normalization, async OCR startup, and adapters. For packaging changes, launch both Python entrypoints and the built EXE.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit prefixes such as `feat:` and `docs:`. Keep commits focused and avoid staging generated `build/`, `dist/`, `ocr_app.log`, or personal settings changes unless intentionally updating release artifacts. Pull requests should describe the user-visible change, list verification commands, note manual OCR/Excel checks, and include screenshots for UI changes.

## Security & Configuration Tips

Keep OCR and Excel processing local. Do not commit production spreadsheets, screenshots, benchmark crops, API keys, or machine-specific paths. `settings.json`, `.analysis_tmp/`, `tests/fixtures/ocr_crops/`, and benchmark JSON files are ignored because they can contain coordinates, network paths, screenshots, and raw OCR text.
