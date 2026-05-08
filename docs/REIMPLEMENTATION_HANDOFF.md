# Reimplementation Handoff

Date: 2026-05-08

## Scope

This handoff summarizes the current CheckOCR2 modernization state. The app must
continue to behave like the existing Tkinter OCR tool while the internals are
split into smaller, testable modules. Treat GUI parity as the release contract:
operators should keep the same buttons, shortcuts, Korean labels, Excel flow,
capture tools, presets, grid behavior, output naming, and stop/final-export
behavior.

## Current Verified State

- Canonical launchers remain available: `check_capture_ocr.py`,
  `Check_Capture_Excel_V6.1_배포.py`, and `python -m checkocr2.main`.
- Runtime settings are stored under `%APPDATA%\CheckOCR2\settings.json`; the
  repo keeps `settings.example.json` only.
- EasyOCR initializes after the GUI appears. OCR start is disabled until the
  app reaches `Ready`.
- Workflow, OCR, Excel, table, settings, paths, image-processing, runtime-state,
  run-report, queue-dispatch, and file/coordinates/timing/options/log panel
  seams now have test coverage.
- JSON run reports capture row timing, blank fields, status counts, export
  timing, failure reasons, and optional OCR confidence fields.
- Benchmark tooling exists for OCR crops, matrix sweeps, `detail` mode, and
  field-specific allowlists.
- Package smoke verifies build metadata, OCR-ready startup, package size,
  startup budget, and absence of forbidden GUI/contrib OpenCV metadata.
- PyInstaller no longer broadly collects all Torch submodules; targeted Torch
  imports plus PyInstaller's Torch hooks are verified by clean build, fast
  startup smoke, and real packaged EasyOCR initialization smoke.

Latest full gate result: `ruff` passed, `pytest` passed with 87 tests,
`compileall` passed, clean PyInstaller release build completed after
hidden-import cleanup, real package smoke passed at about `596.35 MB` with
startup `1.141` seconds, and the full test suite passed with 90 tests after
options-panel extraction.

## Commands To Re-Run Before Release

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5
```

Use the clean release venv for PyInstaller. The global interpreter is expected
to fail release preflight on this machine when GUI/contrib OpenCV packages are
installed outside the release environment.

## Evidence Gates Not Yet Cleared

- Create real OCR crop fixtures under ignored `tests/fixtures/ocr_crops/` with
  `ground_truth.csv`.
- Run a same-input 10-row live OCR comparison before reducing wait defaults or
  changing OCR defaults.
- Benchmark alternate OCR engines only after the fixture baseline exists.
- Continue trimming PyInstaller hidden imports only when each removal is
  followed by a clean build and package smoke.
- Continue GUI/dialog/worker extraction only while `docs/GUI_PARITY_CHECKLIST.md`
  and automated tests stay green.

## Recommended Next Order

1. Build representative date/rate crop fixtures and record the baseline.
2. Run the 10-row live comparison and save run reports under `.analysis_tmp/`.
3. Use `scripts\benchmark_ocr_matrix.py` to compare preprocessing, `detail=1`,
   confidence thresholds, and field allowlists.
4. Tune waits or OCR defaults only if accuracy does not regress.
5. Reduce packaging size through one PyInstaller or dependency change at a time.
6. Extract the remaining GUI panels and dialogs in small parity-checked commits.
