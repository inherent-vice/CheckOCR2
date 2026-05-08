# Implementation Status

Date: 2026-05-08

## Completed

- Preserved all three Python entry paths:
  `check_capture_ocr.py`, `Check_Capture_Excel_V6.1_배포.py`, and
  `python -m checkocr2.main`.
- Moved reusable logic into `checkocr2/` modules for settings, models, events,
  paths, image processing, OCR text normalization, Excel I/O, table rows, OCR
  engine access, screen automation, worker helpers, workflow execution, run
  reports, and runtime UI state.
- Migrated runtime settings from tracked `settings.json` to
  `%APPDATA%\CheckOCR2\settings.json`; the repo keeps only
  `settings.example.json`.
- Made EasyOCR initialization asynchronous so the GUI appears before model load
  completes. OCR start remains disabled until the reader is ready.
- Added explicit GUI states: `Starting`, `OCR Loading`, `Ready`, `Running`,
  `Stopping`, and `Error`.
- Routed OCR row processing through a workflow seam while preserving existing
  capture/OCR behavior and GUI queue events.
- Added JSON OCR run reports next to exported workbooks with per-row timing,
  blank-field counts, status counts, export timing, and failure reasons.
- Stopped full-area screenshot capture and saving unless detailed image saving
  is enabled; date/rate crop capture still runs normally.
- Added benchmark and package-smoke scripts:
  `scripts/benchmark_ocr.py` and `scripts/package_smoke.py`.
- Added `scripts/benchmark_ocr_matrix.py` to run preprocessing/detail
  combinations and summarize candidate regressions against a fixed baseline.
- Added field-specific EasyOCR allowlist benchmarking for date/rate crops,
  exposed through `--allowlist-mode field` and matrix `--allowlist-modes`.
- Split dependency entry files into runtime, build, and dev layers with direct
  dependency pins in `constraints.txt`.
- Added packaged build metadata with app version, build date, Python version,
  direct dependency versions, and dependency hash.
- Added explicit package-smoke OCR readiness mode so the packaged EXE can prove
  the GUI reaches `Ready` without loading real OCR models during smoke tests.
- Extracted the first low-risk UI panel into `checkocr2/ui/panels/log_panel.py`
  while keeping the main GUI controller behavior intact.
- Added root and technical documentation:
  `README.md`, `docs/ARCHITECTURE.md`, updated `docs/PROJECT_OVERVIEW.md`, and
  this status document.
- Added pytest coverage for settings migration, path helpers, Excel I/O, table
  behavior, OCR text parsing, async OCR init, runtime state, OCR engine adapter,
  screen automation, worker helper, workflow behavior, run reports, benchmark
  safety, benchmark matrix behavior, and package smoke logic.
- Added direct coverage that OCR start is rejected while OCR is still loading
  and that a mixed success/KBP-skip/capture-failure 3-row workflow preserves
  event order and finalization counts.
- Added benchmark report coverage for exact accuracy, blank count,
  false-positive count, P95 latency, and confidence fields using fake OCR.

## Verification

Run this full gate before release or push:

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python -m PyInstaller build_app.spec --noconfirm
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready
```

Manual GUI smoke remains required after startup, threading, UI state, or
packaging changes. Launch the canonical app, compatibility launcher, and package
launcher, then confirm the window title and OCR-ready transition.

Latest verification on 2026-05-08:

- `python -m ruff check .`: passed.
- `python -m pytest --basetemp $env:TEMP\checkocr2-pytest`: 62 passed.
- `python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py`: passed.
- `python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture`: dry-run passed with zero fixtures.
- `python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --output-json .analysis_tmp\ocr_benchmark_matrix.json`: dry-run matrix report written.
- `python -m pytest tests\test_ocr_engine.py tests\test_benchmark_script.py tests\test_benchmark_matrix_script.py --basetemp $env:TEMP\checkocr2-allowlist-pytest`: 11 passed for field allowlist benchmark coverage.
- Python GUI smoke passed for the canonical launcher, compatibility launcher,
  and `python -m checkocr2.main`; each showed `📊 Check Capture OCR V6.1`.
- `python -m PyInstaller build_app.spec --noconfirm`: build completed.
- `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready`: passed with package size `1868.403 MB`, metadata, and `Ready` state in the report.

Known build warnings: PyInstaller still reports optional `tensorboard` collection
failure for `torch.utils.tensorboard` and missing `tbb12.dll` for a numba TBB
pool dependency. These warnings did not block the packaged GUI smoke.

## Remaining Evidence Gates

- Build real OCR crop fixtures under ignored `tests/fixtures/ocr_crops/` with a
  `ground_truth.csv`.
- Run a same-input 10-row live OCR comparison before reducing wait times or
  changing OCR defaults.
- Benchmark EasyOCR `detail=1`, confidence-based handling, and candidate engines
  only after fixture baselines exist.
- Split runtime/build/dev dependency sets and reduce PyInstaller hidden imports
  further only after package smoke proves each removal.
- Continue extracting UI panels only while the GUI parity checklist and tests
  stay green.
