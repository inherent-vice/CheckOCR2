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
- Added runtime EasyOCR `detail=1` support behind `ocr_detail_level`, with
  optional date/rate confidence thresholds and run-report confidence fields.
- Split dependency entry files into runtime, build, and dev layers with direct
  dependency pins in `constraints.txt`.
- Removed the direct GUI `opencv-python` runtime dependency; EasyOCR's required
  `opencv-python-headless` remains pinned in `constraints.txt`.
- Extended package smoke metadata checks to reject packaged `opencv-python` or
  `opencv-contrib-python` dist-info when a headless-only OpenCV package is
  expected.
- Added a release-build preflight that stops PyInstaller builds from
  contaminated environments where GUI/contrib OpenCV distributions are
  installed.
- Added packaged build metadata with app version, build date, Python version,
  direct dependency versions, and dependency hash.
- Removed stale PyInstaller hidden imports for uninstalled optional packages
  and stopped broad `collect_submodules('torch')` collection; PyTorch is now
  kept to targeted hidden imports plus PyInstaller's own Torch hooks.
- Added explicit package-smoke OCR readiness modes: `fast` for startup smoke
  without model loading and `real` for packaged EasyOCR reader initialization.
- Extracted low-risk UI panels into `checkocr2/ui/panels/file_panel.py`,
  `checkocr2/ui/panels/coordinates_panel.py`,
  `checkocr2/ui/panels/timing_panel.py`,
  `checkocr2/ui/panels/options_panel.py`, and
  `checkocr2/ui/panels/preset_panel.py`, plus
  `checkocr2/ui/panels/grid_panel.py` and `checkocr2/ui/panels/log_panel.py`
  while keeping the main GUI controller behavior intact.
- Extracted legacy Tk queue dispatch into `checkocr2/ui/queue_dispatcher.py`
  with unit coverage for log, dialog, OCR-ready, grid, stopped, and final-export
  events.
- Extracted the top toolbar into `checkocr2/ui/toolbar.py` with coverage for
  OCR start/stop buttons and theme selection.
- Extracted the menu bar into `checkocr2/ui/menu.py` with coverage for command
  labels, accelerators, and callback wiring.
- Added root and technical documentation:
  `README.md`, `docs/ARCHITECTURE.md`, updated `docs/PROJECT_OVERVIEW.md`, and
  this status document.
- Added pytest coverage for settings migration, path helpers, Excel I/O, table
  behavior, OCR text parsing, async OCR init, runtime state, OCR engine adapter,
  screen automation, worker helper, workflow behavior, queue dispatch, run
  reports, benchmark safety, benchmark matrix behavior, and package smoke
  logic.
- Added direct coverage that OCR start is rejected while OCR is still loading
  and that a mixed success/KBP-skip/capture-failure 3-row workflow preserves
  event order and finalization counts.
- Added benchmark report coverage for exact accuracy, blank count,
  false-positive count, P95 latency, and confidence fields using fake OCR.
- Added `scripts/audit_ocr_fixtures.py` to fail loudly until ignored OCR crop
  fixtures are readable, normalized, deduplicated, and large enough for a real
  baseline.
- Added `scripts/compare_run_reports.py` to compare same-input live run reports
  before wait-time or OCR-default changes, including input-workbook matching,
  row identity checks, blank/failure regression checks, and timing validation.

## Verification

Run this code gate before push:

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python -m venv .analysis_tmp\package_venv
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m pip install -r requirements-build.txt
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5
```

Before OCR tuning or release decisions that depend on OCR accuracy, also run:

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp/ocr_fixture_audit.json
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --output-json .analysis_tmp/live_ocr_compare.json
```

Manual GUI smoke remains required after startup, threading, UI state, or
packaging changes. Launch the canonical app, compatibility launcher, and package
launcher, then confirm the window title and OCR-ready transition.

Latest code verification on 2026-05-11:

- `python -m ruff check .`: passed.
- `python -m pytest --basetemp $env:TEMP\checkocr2-pytest`: 106 passed after fixture-audit and live-comparison tooling.
- `python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py`: passed.
- `python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture`: dry-run passed with zero fixtures.
- `python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field --output-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json`: dry-run matrix report written.
- `python -m pytest tests\test_ocr_engine.py tests\test_benchmark_script.py tests\test_benchmark_matrix_script.py --basetemp $env:TEMP\checkocr2-allowlist-pytest`: 11 passed for field allowlist benchmark coverage.
- `python -m pytest tests\test_audit_ocr_fixtures_script.py tests\test_compare_run_reports_script.py --basetemp $env:TEMP\checkocr2-ocr-gates-pytest`: 12 passed for fixture audit and live report comparison coverage.
- `python -m pytest tests\test_ocr_engine.py tests\test_ocr_workflow_manager.py --basetemp $env:TEMP\checkocr2-confidence-pytest`: 14 passed for runtime confidence coverage.
- `python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json`: failed as expected because `tests\fixtures\ocr_crops\ground_truth.csv` does not exist yet; this hard gate remains open.

Latest package verification on 2026-05-08:

- Python GUI smoke passed for the canonical launcher, compatibility launcher,
  and `python -m checkocr2.main`; each showed `📊 Check Capture OCR V6.1`.
- Source GUI fast-OCR smoke passed after queue-dispatch extraction; the Tk app
  wrote package-smoke status with `runtime_state="Ready"` and `ocr_ready=true`.
- Source GUI fast-OCR smoke passed after menu extraction; the Tk
  app opened `📊 Check Capture OCR V6.1` and wrote
  `runtime_state="Ready"` with `ocr_ready=true`.
- Clean release venv build with `$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean`: build completed after PyInstaller hidden-import cleanup.
- Global-interpreter `python -m PyInstaller build_app.spec --noconfirm`: failed by design because this machine has `opencv-python==4.10.0.84` and `opencv-contrib-python==4.10.0.84` installed outside the release venv.
- `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --max-package-size-mb 650 --max-startup-seconds 5`: fast OCR-ready smoke passed with package size `596.349 MB`, startup time `2.234` seconds, metadata, no forbidden OpenCV dist-info, and `Ready` state in the report.
- `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5`: real packaged EasyOCR initialization smoke passed with package size `596.35 MB`, startup time `1.141` seconds, metadata, no forbidden OpenCV dist-info, and `Ready` state in the report.

Known build warnings: PyInstaller still reports optional `tensorboard`
collection failure for `torch.utils.tensorboard`; the clean release venv keeps
that warning non-blocking while package smoke remains green.

## Remaining Evidence Gates

- Build real OCR crop fixtures under ignored `tests/fixtures/ocr_crops/` with a
  `ground_truth.csv`, then pass `scripts\audit_ocr_fixtures.py`.
- Run a same-input 10-row live OCR comparison with
  `scripts\compare_run_reports.py` before reducing wait times or changing OCR
  defaults.
- Benchmark candidate engines only after fixture baselines exist.
- Continue package-size cleanup only one measured PyInstaller/dependency change
  at a time, with clean build and package smoke after each removal.
- Continue extracting UI panels only while the GUI parity checklist and tests
  stay green.
