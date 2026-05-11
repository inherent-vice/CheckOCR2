# Implementation Status

Date: 2026-05-11

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
- Extracted keyboard-shortcut and about dialogs into
  `checkocr2/ui/dialogs.py` with unit coverage for title/text/messagebox
  behavior.
- Extracted OCR-start input validation messages into
  `checkocr2/ui/start_validation.py` with unit coverage for empty-grid,
  output-folder, OCR-loading, OCR-failed, and ready states.
- Extracted preset controller behavior into `checkocr2/ui/presets.py` with
  unit coverage for combo refresh, apply, save, delete, dialog fallback, and
  legacy wrapper delegation.
- Moved grid status summary and progress label formatting into
  `checkocr2/table_model.py`, preserving the existing GUI text.
- Moved grid render value and status-tag decisions into
  `checkocr2/table_model.py`, leaving Treeview mutation in the Tk controller.
- Moved selected-row and selected-rate clipboard text generation into
  `checkocr2/table_model.py`, leaving the Tk controller to handle selection
  indices and clipboard writes only.
- Routed output-folder cleanup through `checkocr2/paths.py`, so the Tk app no
  longer reaches through `OCRWorkflowManager` for path cleanup.
- Moved legacy `grid_update` tuple row mutation into `checkocr2/table_model.py`,
  leaving the Tk controller to handle scroll, refresh, and logging only.
- Added a typed `GridUpdate` parser in `checkocr2/events.py`, keeping legacy
  tuple transport knowledge out of `table_model.py`.
- Added a typed final-export request parser in `checkocr2/events.py`, keeping
  finalization payload validation out of the queue dispatcher.
- Moved `WorkController` into `checkocr2/work_controller.py`, keeping
  run/stop/skip state out of the legacy Tk source file.
- Moved `ThemeManager` into `checkocr2/ui/theme.py`, keeping theme catalog and
  Tk/ttk style application out of the legacy Tk source file.
- Moved capture and area-preview overlay windows into
  `checkocr2/ui/overlays.py`, keeping full-screen coordinate selection outside
  the legacy Tk source file.
- Moved `DataManager` into `checkocr2/data_manager.py`, keeping Excel grid
  state, clipboard paste, row deletion, and export queue events out of the
  legacy Tk source file.
- Moved settings-to-Tk-variable binding into
  `checkocr2/ui/settings_binding.py`, keeping current settings, preset
  application, and advanced option persistence out of the legacy Tk source file.
- Added root and technical documentation:
  `README.md`, `docs/ARCHITECTURE.md`, updated `docs/PROJECT_OVERVIEW.md`, and
  this status document.
- Added `docs/MODERNIZATION_PLAN_KO.md` as a Korean execution summary covering
  GUI parity, target structure, OCR evidence gates, parallel workstreams, and
  next implementation order.
- Added `docs/REIMPLEMENTATION_EXECUTION_GUIDE.md` as the current execution
  guide for safe work slices, OCR evidence gates, GUI parity checks, parallel
  agent coordination, and commit discipline.
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
- Added field-level benchmark summaries and matrix comparisons so date and rate
  regressions, blank-on-expected-nonempty errors, and missing fixture coverage
  are visible separately from combined accuracy.
- Added `scripts/audit_ocr_fixtures.py` to fail loudly until ignored OCR crop
  fixtures are readable, normalized, deduplicated, and large enough for a real
  baseline.
- Added `scripts/prepare_ocr_fixtures.py` to copy saved date/rate detail crops
  into the ignored fixture folder and create a review-required
  `ground_truth_draft.csv` that must be manually verified before promotion to
  `ground_truth.csv`.
- Added `docs/OCR_FIXTURE_WORKFLOW.md` to document the safe crop draft,
  manual-review, audit, benchmark, and live-comparison sequence.
- Added `scripts/compare_run_reports.py` to compare same-input live run reports
  before wait-time or OCR-default changes, including input-workbook matching,
  row identity checks, blank/failure regression checks, and timing validation.
- Added optional live-comparison P95 row-total improvement gating with a
  configurable percentage threshold for speed and wait-time changes.
- Narrowed broad exception handlers in the legacy Tk app for icon setup, Excel
  load/export, clipboard parsing, run-report flushing, OCR image processing,
  folder opening, settings save/load, and status finalization. Remaining broad
  catches are limited to the top-level workflow safety boundary and adapter
  boundaries.
- Normalized corrupt Excel workbook errors through `ExcelIOError` and EasyOCR /
  OpenCV reader failures through `OCREngineError`, preserving row-level OCR
  failure handling while keeping typed catches at the GUI boundary.
- Wrapped Excel writer failures in `ExcelIOError` so finalization and run-report
  handling still complete when openpyxl rejects workbook content.

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
- `python -m pytest --basetemp $env:TEMP\checkocr2-pytest`: 168 passed after final-export parser extraction, grid-update row mutation extraction, grid status/render extraction, OCR-start validation extraction, preset controller extraction, dialog extraction, fixture preparation, fixture-audit, live-comparison, typed exception-boundary coverage, DataManager extraction coverage, and settings-binding extraction coverage.
- `python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py`: passed.
- `python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture`: dry-run passed with zero fixtures.
- `python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field --output-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json`: dry-run matrix report written.
- `python -m pytest tests\test_ocr_engine.py tests\test_benchmark_script.py tests\test_benchmark_matrix_script.py --basetemp $env:TEMP\checkocr2-allowlist-pytest`: 17 passed for field allowlist benchmark coverage and draft-fixture rejection.
- `python -m pytest tests\test_audit_ocr_fixtures_script.py tests\test_compare_run_reports_script.py --basetemp $env:TEMP\checkocr2-ocr-gates-pytest`: 21 passed for fixture audit and live report comparison coverage.
- `python -m pytest tests\test_prepare_ocr_fixtures_script.py --basetemp $env:TEMP\checkocr2-prepare-fixtures`: 8 passed for fixture draft preparation, overwrite protection, run-report prefill, safe output targeting, dry-run, and CLI error handling.
- `python -m pytest tests\test_ocr_engine.py tests\test_ocr_workflow_manager.py --basetemp $env:TEMP\checkocr2-confidence-pytest`: 14 passed for runtime confidence coverage.
- `python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json`: failed as expected because `tests\fixtures\ocr_crops\ground_truth.csv` does not exist yet; this hard gate remains open.
- Broad exception audit now reports only adapter/safety boundaries: the top-level
  workflow safety boundary, Excel/OCR adapter normalization, and the two
  workflow adapter boundaries:
  `rg -n "except Exception|except BaseException|except:" check_capture_ocr.py checkocr2 scripts tests`.
- `python -m pytest tests\test_data_manager.py tests\test_excel_table_modules.py tests\test_ocr_engine.py tests\test_ocr_workflow_manager.py --basetemp $env:TEMP\checkocr2-review-fixes-pytest`: 26 passed for corrupt workbook, Excel writer, and OCR reader failure regressions.
- `python -m pytest tests\test_dialogs.py tests\test_menu.py tests\test_logging_and_main.py --basetemp $env:TEMP\checkocr2-dialog-review-pytest`: 7 passed for dialog extraction, wrapper delegation, and help-menu wiring.
- `python -m pytest tests\test_start_validation.py tests\test_async_ocr_initialization.py --basetemp $env:TEMP\checkocr2-start-validation-pytest`: 10 passed for OCR-start validation and loading-state behavior.
- `python -m pytest tests\test_excel_table_modules.py tests\test_queue_dispatcher.py tests\test_workflow_module.py --basetemp $env:TEMP\checkocr2-grid-update-green`: 16 passed for legacy grid-update row mutation, queue dispatch, clipboard selection text, grid status summary text, and shared workflow error-status constants.
- `python -m pytest tests\test_queue_dispatcher.py tests\test_workflow_module.py --basetemp $env:TEMP\checkocr2-finalize-parser-green`: 11 passed for final-export payload parsing and workflow event compatibility.
- `python -m pytest tests\test_work_controller.py tests\test_async_ocr_initialization.py tests\test_ocr_workflow_manager.py --basetemp $env:TEMP\checkocr2-work-controller-green`: 17 passed for package-level work controller behavior and OCR workflow compatibility.
- `python -m pytest tests\test_theme_manager.py tests\test_toolbar.py tests\test_coordinates_panel.py --basetemp $env:TEMP\checkocr2-theme-extract2`: 4 passed for package-level theme manager behavior and UI consumers.
- Source GUI fast-OCR smoke after theme extraction opened `📊 Check Capture OCR V6.1`, reached `Ready` with `ocr_ready=true`, and reported `theme_module="checkocr2.ui.theme"`.
- Source GUI fast-OCR smoke after overlay extraction opened `📊 Check Capture OCR V6.1`, reached `Ready` with `ocr_ready=true`, and reported `PointCaptureOverlay.__module__="checkocr2.ui.overlays"`.
- Source GUI fast-OCR smoke after data-manager extraction opened `📊 Check Capture OCR V6.1`, reached `Ready` with `ocr_ready=true`, and reported `data_manager_module="checkocr2.data_manager"`.
- Source GUI fast-OCR smoke after settings-binding extraction used isolated temporary `APPDATA`, opened `📊 Check Capture OCR V6.1`, and reached `Ready` with `ocr_ready=true`.
- Source GUI fast-OCR smoke after grid-render helper extraction used isolated temporary `APPDATA`, opened `📊 Check Capture OCR V6.1`, and reached `Ready` with `ocr_ready=true`.
- Source GUI fast-OCR smoke after preset-controller extraction used isolated temporary `APPDATA`, opened `📊 Check Capture OCR V6.1`, and reached `Ready` with `ocr_ready=true`.

Latest package verification on 2026-05-08:

- Python GUI smoke passed for the canonical launcher, compatibility launcher,
  and `python -m checkocr2.main`; each showed `📊 Check Capture OCR V6.1`.
- Source GUI fast-OCR smoke passed after queue-dispatch extraction; the Tk app
  wrote package-smoke status with `runtime_state="Ready"` and `ocr_ready=true`.
- Source GUI fast-OCR smoke passed after menu extraction; the Tk
  app opened `📊 Check Capture OCR V6.1` and wrote
  `runtime_state="Ready"` with `ocr_ready=true`.
- Source GUI fast-OCR smoke passed after dialog extraction; the Tk app opened
  `📊 Check Capture OCR V6.1` and wrote `runtime_state="Ready"` with
  `ocr_ready=true`.
- Clean release venv build with `$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean`: build completed after PyInstaller hidden-import cleanup.
- Global-interpreter `python -m PyInstaller build_app.spec --noconfirm`: failed by design because this machine has `opencv-python==4.10.0.84` and `opencv-contrib-python==4.10.0.84` installed outside the release venv.
- `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --max-package-size-mb 650 --max-startup-seconds 5`: fast OCR-ready smoke passed with package size `596.349 MB`, startup time `2.234` seconds, metadata, no forbidden OpenCV dist-info, and `Ready` state in the report.
- `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5`: real packaged EasyOCR initialization smoke passed with package size `596.35 MB`, startup time `1.141` seconds, metadata, no forbidden OpenCV dist-info, and `Ready` state in the report.

Known build warnings: PyInstaller still reports optional `tensorboard`
collection failure for `torch.utils.tensorboard`; the clean release venv keeps
that warning non-blocking while package smoke remains green.

## Remaining Evidence Gates

- Build real OCR crop fixtures using `docs/OCR_FIXTURE_WORKFLOW.md`, promote a
  manually reviewed `ground_truth.csv`, then pass
  `scripts\audit_ocr_fixtures.py`.
- Run a same-input 10-row live OCR comparison with
  `scripts\compare_run_reports.py` before reducing wait times or changing OCR
  defaults.
- Benchmark candidate engines only after fixture baselines exist.
- Continue package-size cleanup only one measured PyInstaller/dependency change
  at a time, with clean build and package smoke after each removal.
- Continue extracting UI panels/dialogs/controller helpers only while the GUI
  parity checklist and tests stay green.
