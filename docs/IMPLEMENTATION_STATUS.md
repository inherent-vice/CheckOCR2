# Implementation Status

Date: 2026-05-08

## Completed

- Preserved both Python launchers: `check_capture_ocr.py` and
  `Check_Capture_Excel_V6.1_배포.py`.
- Moved reusable logic into `checkocr2/` modules for settings, models, events,
  paths, image processing, OCR text normalization, Excel I/O, table rows, OCR
  engine access, and screen automation.
- Migrated runtime settings from tracked `settings.json` to the per-user
  `%APPDATA%\CheckOCR2\settings.json` path. The source repo now keeps only
  `settings.example.json`.
- Made EasyOCR initialization asynchronous so the GUI window appears before the
  model load completes. The OCR start button stays disabled until the engine is
  ready.
- Added `scripts/benchmark_ocr.py` and `docs/OCR_BENCHMARK_PLAN.md` for
  repeatable OCR accuracy and latency benchmarking.
- Added pytest characterization/unit tests for settings migration, path helpers,
  Excel import/export, table behavior, OCR text parsing, async OCR init, OCR
  engine adapter, screen automation adapter, and benchmark safety checks.

## Verification

- `python -m ruff check .`
- `python -m pytest --basetemp $env:TEMP\checkocr2-pytest`
- `python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py`
- `python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture`
- Launched `python check_capture_ocr.py` and confirmed the `📊 Check Capture OCR V6.1`
  window was responsive.
- Launched `python Check_Capture_Excel_V6.1_배포.py` and confirmed the same window.
- Built with `python -m PyInstaller build_app.spec --noconfirm`.
- Launched `dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe` and confirmed the
  packaged window was responsive.

## Remaining Evidence Gates

- Build real OCR crop fixtures under ignored `tests/fixtures/ocr_crops/` before
  changing OCR engine, confidence, or timing defaults.
- Run a live 10-row OCR comparison on the same input before reducing fixed wait
  times.
- Continue extracting `workflow.py` and UI panels only after the current tests
  are kept green.
