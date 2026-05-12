# Implementation Status

Date: 2026-05-12

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
- Moved the default app log from the repository root to
  `%APPDATA%\CheckOCR2\logs\ocr_app.log` and enabled rotating log files so
  normal source/package launches no longer create `ocr_app.log` in the repo
  root.
- Tightened date OCR validation so normalized `YYYY/MM/DD` values must be real
  calendar dates before they are accepted as valid OCR output.
- Moved the legacy `UnifiedSettingsManager` compatibility adapter into
  `checkocr2/settings_compat.py`, preserving fallback-to-default settings after
  load errors and automatic preset `created_at` timestamps.
- Made EasyOCR initialization asynchronous so the GUI appears before model load
  completes. OCR start remains disabled until the reader is ready.
- Extracted asynchronous OCR initialization controller glue into
  `checkocr2/ui/ocr_initialization_actions.py`, preserving already-initializing
  and already-ready no-ops, package-smoke fast OCR readiness, real initializer
  thread launch, and legacy `ocr_ready` queue events.
- Extracted EasyOCR reader startup and fallback behavior into
  `checkocr2/ocr_reader_lifecycle.py`, preserving English/CPU defaults, legacy
  fallback settings reset, fatal error messagebox queueing, and logger text.
- Extracted OCR runtime option lookup into `checkocr2/ocr_runtime_options.py`,
  preserving legacy `ocr_detail_level` parsing and field-specific minimum
  confidence setting keys.
- Extracted temporary date/rate OCR crop cleanup decisions into
  `checkocr2/image_processing.py`, preserving save-detail skip behavior,
  legacy filename matching, deletion success logs, and deletion failure
  warning logs.
- Extracted OCR workflow run setup into `checkocr2/workflow_run_setup.py`,
  preserving paste/load delays, capture-coordinate mapping, input-Excel stem
  detail-image folders, save-folder creation, run-report path, and initial
  report metadata.
- Extracted workflow event queue bridging into
  `checkocr2/workflow_event_bridge.py`, preserving legacy tuple forwarding,
  `grid_update` parsing before queueing, current processing index updates, and
  row-total timing for completed or errored rows.
- Extracted legacy workflow capture and EasyOCR adapters into
  `checkocr2/workflow_legacy_adapters.py`, preserving capture call arguments,
  adapter timing defaults, missing-image behavior, OCR tracking reset, OCR
  timing, and confidence metadata copying.
- Extracted workflow run-report success/failure finalization into
  `checkocr2/workflow_report_finalization.py`, preserving processing-state
  finalization, row-report recording, stopped/error summary values, and flush
  ordering.
- Widened `OcrRow.from_dict()` to accept any `Mapping[str, Any]`, preserving
  legacy grid dictionaries while matching workflow row snapshots that are typed
  as mutable or read-only mappings.
- Added explicit GUI states: `Starting`, `OCR Loading`, `Ready`, `Running`,
  `Stopping`, and `Error`.
- Routed OCR row processing through a workflow seam while preserving existing
  capture/OCR behavior and GUI queue events.
- Extracted screen copy/click/paste-wait/screenshot capture into
  `checkocr2/capture_adapter.py`, preserving detail-image saving, date/rate
  in-memory captures, stop handling during waits, invalid-coordinate logs, and
  capture timing fields.
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
- Added `scripts/check_ocr_evidence_bundle.py` to fail closed when OCR evidence
  artifacts are not-ready, dry-run, zero-case, coverage-changed, or
  live-comparison rejected. Exploratory matrix regressions are warnings unless
  `--require-no-matrix-regressions` is used for selected-candidate bundles.
- Added runtime EasyOCR `detail=1` support behind `ocr_detail_level`, with
  optional date/rate confidence thresholds and run-report confidence fields.
- Moved date/rate OCR field result decisions and legacy debug-log event text
  into `checkocr2/ocr_field_analysis.py`, leaving the workflow manager to emit
  the same queue events and preserve wrapper compatibility.
- Strengthened date validation from format-only matching to real calendar-date
  validation, so impossible dates such as February 30 are rejected by the same
  invalid-date reporting path.
- Extracted single-field OCR extraction into
  `checkocr2/ocr_field_extraction.py`, preserving image-load/preprocess/OCR/
  parse/total timing keys, confidence metadata, confidence-threshold warnings,
  OCR result log text, temp-image cleanup logs, and blank-field error handling.
- Extracted date/rate OCR image-pair orchestration into
  `checkocr2/ocr_pair_processing.py`, preserving call order, missing-source
  skip behavior, partial-failure return values, Korean error logs, and legacy
  manager wrapper delegation.
- Documented the `OcrFieldAnalysis(value, log_events)` compatibility contract
  in `docs/OCR_FIELD_ANALYSIS_CONTRACT.md`, including exact queue shape,
  default field labels, empty/valid/invalid rules, and focused verification
  commands.
- Moved reusable OCR crop image-source loading and upscaling size/changed-state
  calculation into `checkocr2/image_processing.py`, leaving the legacy workflow
  manager to preserve existing OCR image-load timing, queue log text, object
  fallback behavior, and path-load failure re-raise semantics.
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
- Added explicit PyInstaller excludes for optional TensorFlow, Keras, and
  TensorBoard stacks so they are not bundled if present in the build
  environment.
- Added explicit package-smoke OCR readiness modes: `fast` for startup smoke
  without model loading and `real` for packaged EasyOCR reader initialization.
- Extracted runtime-state UI and package-smoke status side effects into
  `checkocr2/ui/runtime_status_actions.py`, preserving start/stop button
  updates, OCR-ready/error mapping, env-disabled no-op behavior, and status
  write failure logging.
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
- Extracted global keyboard shortcut binding and F5 run/stop dispatch into
  `checkocr2/ui/keyboard_actions.py`, preserving focus setup, shortcut
  sequences, callback wiring, and running-vs-idle F5 behavior.
- Extracted application shutdown lifecycle behavior into
  `checkocr2/ui/lifecycle_actions.py`, preserving idle destroy, running-work
  stop request, worker join timeout, timeout warning, join-error logging, and
  legacy wrapper delegation.
- Extracted startup window centering into `checkocr2/ui/window_actions.py`,
  preserving update-before-measure behavior, integer-centered geometry, large
  window negative offsets, and legacy wrapper delegation.
- Extracted shared styled section-frame construction into
  `checkocr2/ui/section_frame.py`, preserving outer-frame theme registration,
  title label styling, default and fill-parent packing, returned content-frame
  behavior, and positional legacy wrapper compatibility.
- Extracted file and output-folder dialog path preparation into
  `checkocr2/ui/file_dialogs.py`, preserving Excel-parent output defaults,
  single-slash UNC normalization, and server-share fallback for folder
  selection.
- Extracted Excel and output-folder UI actions into
  `checkocr2/ui/folder_actions.py`, preserving Excel file selection,
  output-folder auto-fill, output-folder selection, Windows Explorer fallback,
  local folder creation prompts, UNC server warnings, and macOS/Linux SMB
  command conversion.
- Extracted Excel grid-load UI action glue into `checkocr2/ui/folder_actions.py`,
  preserving missing-file messagebox behavior, DataManager ownership of load
  errors, cleaned parent output-folder auto-fill, success logs, and grid
  refresh only when rows are loaded.
- Extracted application icon selection and Tk icon application into
  `checkocr2/ui/icons.py`, preserving the existing icon candidate priority and
  `_icon_photos` retention behavior.
- Extracted log text-widget update behavior into `checkocr2/ui/log_actions.py`,
  preserving normal/disabled state transitions, level-tag fallback, insert,
  scroll-to-end, and legacy wrapper delegation.
- Extracted top-level main-window layout assembly into
  `checkocr2/ui/main_window.py` with unit coverage for menu/toolbar dispatch,
  three-panel layout, left-panel section order, and log handler wiring.
- Extracted package-smoke runtime status payload creation and file writing into
  `checkocr2/package_smoke_status.py`, leaving the Tk app to delegate status
  reporting only.
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
- Extracted grid button and clipboard action glue into
  `checkocr2/ui/grid_actions.py`, preserving add-row scrolling, paste
  reporting, selected-row deletion confirmation, clear-all confirmation, and
  row/rate clipboard copy messages.
- Moved grid context-menu construction into `checkocr2/ui/grid_actions.py`,
  preserving menu labels, ordering, command wiring, theme registration,
  popup coordinates, and `grab_release` cleanup.
- Extracted grid cell-edit action glue into
  `checkocr2/ui/grid_edit_actions.py`, preserving double-click entry creation,
  theme registration, enter/focus-out save behavior, escape cancellation, and
  legacy wrapper delegation.
- Extracted grid refresh and status-label action glue into
  `checkocr2/ui/grid_refresh_actions.py`, preserving Treeview clear/insert
  order, render values/tags, and status/progress label updates.
- Extracted grid status-tag styling into `checkocr2/ui/grid_refresh_actions.py`,
  preserving `processing`, `completed`, and `error` tag names plus theme color
  keys and fallback colors.
- Extracted OCR run/stop button orchestration into
  `checkocr2/ui/ocr_actions.py`, preserving validation gating, stop delegation,
  running-state transition, worker launch arguments, and queued stop logging.
- Extracted OCR-start input-validation UI glue into
  `checkocr2/ui/ocr_actions.py`, preserving output-folder trimming,
  validator ordering, OCR loading/ready checks, warning-vs-error messagebox
  dispatch, `parent=app`, and legacy wrapper compatibility.
- Extracted OCR upscaling detail toggle behavior into
  `checkocr2/ui/options_actions.py`, preserving child show/hide behavior,
  missing-frame tolerance, advanced-settings persistence, and legacy wrapper
  compatibility.
- Extracted work-completion and stopped-work UI finalization into
  `checkocr2/ui/completion_actions.py`, preserving controller reset,
  runtime-state restoration, grid refresh, quick settings save, stopped-state
  finalization, and stopped dialog text.
- Extracted UI processing-state finalization into
  `checkocr2/ui/completion_actions.py`, preserving shared workflow status
  finalization, legacy app/workflow-manager wrapper delegation, success log
  queue messages, and malformed-row error logging.
- Extracted OCR completion summary text creation into
  `checkocr2/ui/completion_actions.py`, preserving the exact user-visible
  multiline summary and legacy app/workflow-manager wrapper signatures.
- Extracted final-export completion into
  `checkocr2/ui/completion_actions.py`, preserving Excel export, fallback
  output naming, run-report row timing/confidence fields, export timing,
  flush behavior, work reset behavior, grid refresh, and success/error dialogs.
- Extracted coordinate capture and preview action glue into
  `checkocr2/ui/coordinate_actions.py`, preserving click-point relocation,
  all/date/rate area relocation, preview payload construction, and legacy app
  wrapper delegation.
- Routed output-folder cleanup through `checkocr2/paths.py`, so the Tk app no
  longer reaches through `OCRWorkflowManager` for path cleanup.
- Moved legacy `grid_update` tuple row mutation into `checkocr2/table_model.py`,
  leaving the Tk controller to handle scroll, refresh, and logging only.
- Added a typed `GridUpdate` parser in `checkocr2/events.py`, keeping legacy
  tuple transport knowledge out of `table_model.py`.
- Extracted legacy grid-update queue handling into
  `checkocr2/ui/grid_update_actions.py`, preserving row mutation delegation,
  processing-row scrolling, debug logging, refresh behavior, and malformed
  payload error logging.
- Added a typed final-export request parser in `checkocr2/events.py`, keeping
  finalization payload validation out of the queue dispatcher.
- Moved `WorkController` into `checkocr2/work_controller.py`, keeping
  run/stop/skip state out of the legacy Tk source file.
- Added locked `WorkController` mutations plus a `WorkStateSnapshot` view, and
  routed package workflow current-item/skip updates through the controller
  setters when available.
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
- Extracted current settings load/save action glue into
  `checkocr2/ui/settings_actions.py`, preserving saved-path restoration,
  missing-current-settings advanced defaults, preset refresh, theme restore,
  advanced reset, quick-save advanced persistence, error logging, and
  messagebox reporting.
- Added root and technical documentation:
  `README.md`, `docs/ARCHITECTURE.md`, updated `docs/PROJECT_OVERVIEW.md`, and
  this status document.
- Added `docs/MODERNIZATION_PLAN_KO.md` as a Korean execution summary covering
  GUI parity, target structure, OCR evidence gates, parallel workstreams, and
  next implementation order.
- Added `docs/REIMPLEMENTATION_STATUS_KO.md` as a Korean current-state
  document covering the verified baseline, preserved GUI contract, extracted
  module boundaries, OCR speed/accuracy gates, next order, and verification
  commands.
- Added `docs/REIMPLEMENTATION_AGENT_PLAN_KO.md` as the Korean parallel-agent
  reimplementation plan covering stream ownership, GUI invariants, execution
  order, and open evidence gates.
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
- Added `scripts/source_gui_smoke.py` to run repeatable source launcher smokes
  with window-title matching, window-size validation, clean-exit validation,
  fast OCR Ready status, isolated `APPDATA`, settings-file verification, JSON
  evidence, and clean process termination.
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
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5 --min-window-width 1000 --min-window-height 600 --require-clean-exit
```

Before OCR tuning or release decisions that depend on OCR accuracy, also run:

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp/ocr_fixture_audit.json
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --output-json .analysis_tmp/live_ocr_compare.json
```

Manual GUI smoke remains required after startup, threading, UI state, or
packaging changes. Launch the canonical app, compatibility launcher, and package
launcher, then confirm the window title and OCR-ready transition.

For date/rate OCR field parsing changes, also review
`docs/OCR_FIELD_ANALYSIS_CONTRACT.md` and preserve the documented
`OcrFieldAnalysis(value, log_events)` contract before changing helper or manager
behavior.

Latest code verification on 2026-05-12:

- `python -m ruff check .`: passed.
- `python -m pytest --basetemp $env:TEMP\checkocr2-pytest-date-package`: 429 passed after adding real-date OCR validation coverage, WorkController lock/snapshot coverage, APPDATA rotating-log coverage, log-panel parity coverage, coordinate/options/workflow parity coverage, file/folder/grid parity coverage, source/package smoke clean-exit validation coverage, close-request failure regressions, false-positive regressions for already-exited processes, source failure-path coverage, source/package smoke window-size validation coverage, the OCR evidence-bundle gate, GUI parity evidence update, OCR pair-processing slice, OCR field-extraction slice, the `OcrRow.from_dict()` mapping-compatibility slice, and previous workflow report-finalization, workflow legacy-adapter, workflow event-bridge, OCR workflow run-setup, OCR temp-cleanup, OCR runtime-options, OCR reader lifecycle, OCR initialization action, OCR field-analysis, settings compatibility adapter, OCR upscaling helper, section-frame builder, window-centering action, app lifecycle action, processing-state finalization action, final-export completion action, final-export parser, grid-update row mutation, grid status/render, grid-action, grid context-menu, grid-edit action, grid-refresh action, grid-tag styling, grid-update action, keyboard-action, runtime-status action, settings-action, log-action, OCR run/stop and input-validation action, options-action, work-completion and summary action, coordinate capture/preview action, Excel load/output-folder action, source GUI smoke, screen-capture adapter, OCR-start validation, preset controller, dialog, file-dialog path, application-icon, main-window layout, package-smoke status, package-smoke settings-file enforcement, fixture preparation, fixture-audit, live-comparison, typed exception-boundary, DataManager extraction, and settings-binding extraction coverage.
- `python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py`: passed.
- `python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture`: dry-run passed with zero fixtures.
- `python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field --output-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json`: dry-run matrix report written.
- `python -m pytest tests\test_menu.py tests\test_toolbar.py tests\test_keyboard_actions.py tests\test_icons.py --basetemp $env:TEMP\checkocr2-parity-menu-toolbar-shortcuts-icons`: 9 passed for GUI parity evidence on menu cascades/commands, toolbar title/start/stop/theme selector, keyboard shortcuts, F5 run/stop dispatch, and preferred ICO/PNG source icon application.
- `python -m pytest tests\test_folder_actions.py tests\test_excel_table_modules.py tests\test_data_manager.py tests\test_grid_panel.py tests\test_grid_actions.py tests\test_grid_edit_actions.py tests\test_grid_refresh_actions.py --basetemp $env:TEMP\checkocr2-file-grid-parity2`: 59 passed for GUI parity evidence on Excel browse/load/export, output-folder local/UNC behavior, Korean Excel headers, `_updated.xlsx` output naming, `OCR_Results` sheet naming, grid columns, row add/paste/delete/clear, cell editing, context menu commands, grid shortcuts, and status tags.
- `python -m pytest tests\test_coordinate_actions.py tests\test_coordinates_panel.py tests\test_settings_binding.py tests\test_settings_actions.py tests\test_settings_compat.py tests\test_settings_store_lifecycle.py tests\test_options_actions.py tests\test_options_panel.py tests\test_presets.py tests\test_preset_panel.py tests\test_start_validation.py tests\test_workflow_module.py tests\test_workflow_report_finalization.py tests\test_completion_actions.py --basetemp $env:TEMP\checkocr2-coordinate-options-workflow-parity`: 72 passed for GUI parity evidence on coordinate relocation and preview payloads, overlay `Esc`, option persistence, preset save/apply/delete/lifecycle, OCR start validation, KBP skip, processing/stopped workflow events, workflow report finalization, and export completion summaries.
- `python -m pytest tests\test_log_actions.py tests\test_log_panel.py tests\test_logging_and_main.py tests\test_queue_dispatcher.py --basetemp $env:TEMP\checkocr2-log-core-parity`: 18 passed for GUI parity evidence on `INFO`, `WARNING`, `ERROR`, and `SUCCESS` log-widget insertion, APPDATA rotating file logging, Tk log-handler forwarding, queue dispatch, and log panel construction.
- `python -m pytest tests\test_package_helpers.py tests\test_ocr_field_analysis.py --basetemp $env:TEMP\checkocr2-date-validation`: 26 passed for date/rate OCR helper coverage, including rejection of non-calendar date strings such as `2024/02/30` and `2024/13/01`.
- `.\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm`: clean release venv package build passed; global `python -m PyInstaller build_app.spec --noconfirm` still fails by design on this machine because global Python contains GUI/contrib OpenCV packages.
- `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5 --min-window-width 1000 --min-window-height 600 --require-clean-exit`: real package smoke passed on the fresh build with package size `596.405 MB`, startup `4.36` seconds, window size `1216x889`, clean exit code `0`, build date `2026-05-12T08:57:58+00:00`, isolated settings file, and no forbidden OpenCV dist-info.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45 --min-window-width 1000 --min-window-height 600 --require-clean-exit`: source GUI fast-OCR smoke passed after the clean-exit gate with startup `1.016` seconds, window size `1216x889`, `runtime_state="Ready"`, `ocr_ready=true`, clean GUI exit code `0`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after the OCR pair-processing slice with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after workflow legacy-adapter extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after workflow event-bridge extraction with startup `1.031` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after OCR workflow run-setup extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after OCR temp-cleanup extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after OCR runtime-options extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after OCR reader lifecycle extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after OCR initialization action extraction with startup `1.015` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after OCR field-analysis extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after capture-adapter extraction with startup `1.031` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after grid context-menu extraction with startup `1.031` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after log-action extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after grid-update action extraction with startup `1.015` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after keyboard-action extraction with startup `1.031` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after grid-edit action extraction with startup `1.015` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after grid-refresh action extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after runtime-status action extraction with startup `1.031` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after settings-action extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after grid-tag styling extraction with startup `1.031` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after Excel-load action extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed after OCR input-validation action extraction with startup `1.015` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after options-action extraction with startup `1.032` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after completion-summary extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after final-export completion extraction with startup `1.015` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after processing-state finalization extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after lifecycle-action extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after window-centering action extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after section-frame builder extraction with startup `1.015` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after OCR upscaling helper extraction with startup `1.015` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: source GUI fast-OCR smoke passed after settings compatibility adapter extraction with startup `1.016` seconds, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python -m pytest tests\test_ocr_engine.py tests\test_benchmark_script.py tests\test_benchmark_matrix_script.py --basetemp $env:TEMP\checkocr2-allowlist-pytest`: 17 passed for field allowlist benchmark coverage and draft-fixture rejection.
- `python -m pytest tests\test_audit_ocr_fixtures_script.py tests\test_compare_run_reports_script.py --basetemp $env:TEMP\checkocr2-ocr-gates-pytest`: 21 passed for fixture audit and live report comparison coverage.
- `python -m pytest tests\test_prepare_ocr_fixtures_script.py --basetemp $env:TEMP\checkocr2-prepare-fixtures`: 8 passed for fixture draft preparation, overwrite protection, run-report prefill, safe output targeting, dry-run, and CLI error handling.
- `python -m pytest tests\test_ocr_engine.py tests\test_ocr_workflow_manager.py --basetemp $env:TEMP\checkocr2-confidence-pytest`: 14 passed for runtime confidence coverage.
- `python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json`: failed as expected with `ready_for_baseline=false` and `Fixture CSV not found: tests\fixtures\ocr_crops\ground_truth.csv`; this hard gate remains open.
- Broad exception audit now reports only adapter/safety boundaries: the top-level
  workflow safety boundary, Excel/OCR adapter normalization, and the two
  workflow adapter boundaries:
  `rg -n "except Exception|except BaseException|except:" check_capture_ocr.py checkocr2 scripts tests`.
- `python -m pytest tests\test_data_manager.py tests\test_excel_table_modules.py tests\test_ocr_engine.py tests\test_ocr_workflow_manager.py --basetemp $env:TEMP\checkocr2-review-fixes-pytest`: 26 passed for corrupt workbook, Excel writer, and OCR reader failure regressions.
- `python -m pytest tests\test_dialogs.py tests\test_menu.py tests\test_logging_and_main.py --basetemp $env:TEMP\checkocr2-dialog-review-pytest`: 7 passed for dialog extraction, wrapper delegation, and help-menu wiring.
- `python -m pytest tests\test_keyboard_actions.py tests\test_menu.py tests\test_dialogs.py tests\test_ocr_actions.py --basetemp $env:TEMP\checkocr2-keyboard-actions-green`: 12 passed for keyboard shortcut binding, F5 run/stop dispatch, legacy wrapper delegation, menu wiring, dialogs, and OCR action compatibility.
- `python -m pytest tests\test_grid_edit_actions.py tests\test_grid_actions.py tests\test_grid_panel.py --basetemp $env:TEMP\checkocr2-grid-edit-focused2`: 21 passed for double-click cell editing, save/cancel/focus-out behavior, legacy wrapper delegation, existing grid actions, and grid-panel compatibility.
- `python -m pytest tests\test_grid_refresh_actions.py tests\test_grid_update_actions.py tests\test_excel_table_modules.py tests\test_grid_panel.py --basetemp $env:TEMP\checkocr2-grid-refresh-green`: 19 passed for Treeview redraw, status/progress labels, legacy wrapper delegation, grid-update compatibility, table-model rendering, and grid-panel compatibility.
- `python -m pytest tests\test_runtime_status_actions.py tests\test_async_ocr_initialization.py tests\test_runtime_state.py tests\test_package_smoke_status.py tests\test_queue_dispatcher.py --basetemp $env:TEMP\checkocr2-runtime-status-focused`: 23 passed for runtime-state button updates, OCR-ready/error mapping, package-smoke status writes, no-smoke-env behavior, async OCR initialization, and queue-dispatch compatibility.
- `python -m pytest tests\test_file_dialogs.py tests\test_file_panel.py tests\test_menu.py --basetemp $env:TEMP\checkocr2-file-dialogs-final`: 7 passed for file-dialog path preparation, file-panel compatibility, and menu wiring.
- `python -m pytest tests\test_folder_actions.py tests\test_file_dialogs.py tests\test_file_panel.py tests\test_menu.py --basetemp $env:TEMP\checkocr2-folder-actions-green3`: 17 passed for Excel/output-folder action behavior, file-dialog path preparation, file-panel compatibility, and menu wiring.
- `python -m pytest tests\test_source_gui_smoke_script.py tests\test_package_smoke_script.py --basetemp $env:TEMP\checkocr2-source-smoke-green4`: 36 passed for source GUI smoke and packaged EXE smoke script behavior, including malformed source-entrypoint JSON error reporting.
- `python -m pytest tests\test_capture_adapter.py tests\test_ocr_workflow_manager.py tests\test_workflow_module.py --basetemp $env:TEMP\checkocr2-capture-adapter-review-fix`: 25 passed for screen-capture adapter behavior, legacy workflow-manager wrapper compatibility, workflow event behavior, and load-wait cancellation coverage.
- `python -m pytest tests\test_grid_actions.py tests\test_grid_panel.py tests\test_excel_table_modules.py --basetemp $env:TEMP\checkocr2-grid-actions-fix`: 17 passed for grid action delegation, stable delete selection confirmation, grid-panel compatibility, and table-model clipboard behavior.
- `python -m pytest tests\test_grid_actions.py tests\test_grid_panel.py tests\test_excel_table_modules.py --basetemp $env:TEMP\checkocr2-context-menu-green3`: 20 passed for grid action delegation, legacy context-menu wrapper delegation, menu construction, menu command wiring, grab cleanup, grid-panel compatibility, and table-model clipboard behavior.
- `python -m pytest tests\test_log_actions.py tests\test_log_panel.py tests\test_logging_and_main.py tests\test_queue_dispatcher.py --basetemp $env:TEMP\checkocr2-log-actions-green`: 13 passed for log text-widget updates, legacy wrapper delegation, log-panel construction, logger setup, and queue-dispatch compatibility.
- `python -m pytest tests\test_ocr_actions.py tests\test_async_ocr_initialization.py tests\test_work_controller.py --basetemp $env:TEMP\checkocr2-ocr-actions-green2`: 11 passed for OCR run/stop action orchestration, legacy app wrapper delegation, async OCR initialization, and work-controller compatibility.
- `python -m pytest tests\test_ocr_actions.py tests\test_start_validation.py tests\test_async_ocr_initialization.py --basetemp $env:TEMP\checkocr2-validate-inputs-reviewfix`: 20 passed for OCR input validation, warning/error dialog routing, legacy wrapper delegation, start-validation compatibility, and async OCR-loading start blocking.
- `python -m pytest tests\test_options_actions.py tests\test_options_panel.py tests\test_settings_binding.py --basetemp $env:TEMP\checkocr2-options-actions-focused`: 12 passed for upscaling detail show/hide behavior, missing-frame tolerance, legacy wrapper delegation, options-panel wiring, and settings binding compatibility.
- `python -m pytest tests\test_completion_actions.py tests\test_queue_dispatcher.py tests\test_ocr_workflow_manager.py --basetemp $env:TEMP\checkocr2-summary-actions-reviewfix`: 23 passed for exact OCR completion summary text, legacy app/workflow-manager summary wrapper delegation, queue-dispatch compatibility, and workflow-manager compatibility.
- `python -m pytest tests\test_completion_actions.py tests\test_queue_dispatcher.py --basetemp $env:TEMP\checkocr2-completion-actions-green2`: 8 passed for work-completion action behavior, stopped-work finalization, legacy app wrapper delegation, and queue-dispatch compatibility.
- `python -m pytest tests\test_coordinate_actions.py tests\test_coordinates_panel.py tests\test_overlays.py --basetemp $env:TEMP\checkocr2-coordinate-actions-green2`: 12 passed for coordinate action behavior, legacy app wrapper delegation, coordinates-panel compatibility, and overlay compatibility.
- `python -m pytest tests\test_main_window.py tests\test_file_panel.py tests\test_grid_panel.py tests\test_log_panel.py tests\test_toolbar.py tests\test_menu.py --basetemp $env:TEMP\checkocr2-main-window`: 8 passed for main-window layout assembly and existing panel/menu/toolbar builders.
- `python -m pytest tests\test_icons.py --basetemp $env:TEMP\checkocr2-icons2`: 4 passed for icon candidate priority, ICO/PNG application, missing-icon handling, and legacy wrapper delegation.
- `python -m pytest tests\test_package_smoke_script.py --basetemp $env:TEMP\checkocr2-package-smoke-settings`: 29 passed for package metadata, OCR-ready, isolated `APPDATA`, settings-file location, cleanup failure handling, relative `APPDATA` resolution, OpenCV distribution, size, startup, and process-handling smoke coverage.
- `python -m pytest tests\test_package_smoke_status.py tests\test_async_ocr_initialization.py tests\test_runtime_state.py --basetemp $env:TEMP\checkocr2-package-smoke-status4`: 10 passed for package-smoke status payload writing, fast OCR env handling, env-disabled no-op behavior, async OCR initialization, and runtime state UI behavior.
- `python -m pytest tests\test_start_validation.py tests\test_async_ocr_initialization.py --basetemp $env:TEMP\checkocr2-start-validation-pytest`: 10 passed for OCR-start validation and loading-state behavior.
- `python -m pytest tests\test_excel_table_modules.py tests\test_queue_dispatcher.py tests\test_workflow_module.py --basetemp $env:TEMP\checkocr2-grid-update-green`: 16 passed for legacy grid-update row mutation, queue dispatch, clipboard selection text, grid status summary text, and shared workflow error-status constants.
- `python -m pytest tests\test_grid_update_actions.py tests\test_queue_dispatcher.py tests\test_workflow_module.py tests\test_excel_table_modules.py --basetemp $env:TEMP\checkocr2-grid-update-actions-green2`: 23 passed for grid-update action scroll/refresh/logging behavior, malformed payload logging, legacy wrapper delegation, queue dispatch, workflow event compatibility, and table-model row mutation.
- `python -m pytest tests\test_queue_dispatcher.py tests\test_workflow_module.py --basetemp $env:TEMP\checkocr2-finalize-parser-green`: 11 passed for final-export payload parsing and workflow event compatibility.
- `python -m pytest tests\test_work_controller.py tests\test_async_ocr_initialization.py tests\test_ocr_workflow_manager.py --basetemp $env:TEMP\checkocr2-work-controller-green`: 17 passed for package-level work controller behavior and OCR workflow compatibility.
- `python -m pytest tests\test_theme_manager.py tests\test_toolbar.py tests\test_coordinates_panel.py --basetemp $env:TEMP\checkocr2-theme-extract2`: 4 passed for package-level theme manager behavior and UI consumers.
- Source GUI fast-OCR smoke after theme extraction opened `📊 Check Capture OCR V6.1`, reached `Ready` with `ocr_ready=true`, and reported `theme_module="checkocr2.ui.theme"`.
- Source GUI fast-OCR smoke after overlay extraction opened `📊 Check Capture OCR V6.1`, reached `Ready` with `ocr_ready=true`, and reported `PointCaptureOverlay.__module__="checkocr2.ui.overlays"`.
- Source GUI fast-OCR smoke after data-manager extraction opened `📊 Check Capture OCR V6.1`, reached `Ready` with `ocr_ready=true`, and reported `data_manager_module="checkocr2.data_manager"`.
- Source GUI fast-OCR smoke after settings-binding extraction used isolated temporary `APPDATA`, opened `📊 Check Capture OCR V6.1`, and reached `Ready` with `ocr_ready=true`.
- Source GUI fast-OCR smoke after grid-render helper extraction used isolated temporary `APPDATA`, opened `📊 Check Capture OCR V6.1`, and reached `Ready` with `ocr_ready=true`.
- Source GUI fast-OCR smoke after preset-controller extraction used isolated temporary `APPDATA`, opened `📊 Check Capture OCR V6.1`, and reached `Ready` with `ocr_ready=true`.
- Source GUI fast-OCR smoke after main-window layout extraction used isolated
  temporary `APPDATA`, wrote package-smoke status, and reached `Ready` with
  `ocr_ready=true`.
- Source GUI fast-OCR smoke after package-smoke status extraction used isolated
  temporary `APPDATA`, opened `📊 Check Capture OCR V6.1`, wrote status with
  `runtime_state="Ready"`, and reached `ocr_ready=true`.
- Source GUI fast-OCR smoke after application-icon extraction used isolated
  temporary `APPDATA`, opened `📊 Check Capture OCR V6.1`, wrote status with
  `runtime_state="Ready"`, and reached `ocr_ready=true`.

- Source GUI fast-OCR smoke after file-dialog path extraction used isolated
  temporary `APPDATA`, wrote status with `runtime_state="Ready"`, and reached
  `ocr_ready=true`.
- Source GUI fast-OCR smoke after grid-action extraction used isolated
  temporary `APPDATA`, wrote status with `runtime_state="Ready"`, and reached
  `ocr_ready=true`.
- Source GUI fast-OCR smoke after OCR run/stop action extraction used isolated
  temporary `APPDATA`, wrote status with `runtime_state="Ready"`, and reached
  `ocr_ready=true`.
- Source GUI fast-OCR smoke after work-completion action extraction used
  isolated temporary `APPDATA`, wrote status with `runtime_state="Ready"`, and
  reached `ocr_ready=true`.
- Source GUI fast-OCR smoke after coordinate action extraction used isolated
  temporary `APPDATA`, wrote status with `runtime_state="Ready"`, and reached
  `ocr_ready=true`.
- Source GUI fast-OCR smoke after folder action extraction used isolated
  temporary `APPDATA`, wrote status with `runtime_state="Ready"`, and reached
  `ocr_ready=true`.
- `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45`: passed with `window_title="📊 Check Capture OCR V6.1"`, `runtime_state="Ready"`, `ocr_ready=true`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python Check_Capture_Excel_V6.1_배포.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45 --require-clean-exit`: passed with `window_title="📊 Check Capture OCR V6.1"`, `runtime_state="Ready"`, `ocr_ready=true`, window size `1216x889`, clean GUI exit code `0`, isolated settings-file verification, and cleanup.
- `python scripts\source_gui_smoke.py --entrypoint "python -m checkocr2.main" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45 --require-clean-exit`: passed with `window_title="📊 Check Capture OCR V6.1"`, `runtime_state="Ready"`, `ocr_ready=true`, window size `1216x889`, clean GUI exit code `0`, isolated settings-file verification, and cleanup.

Latest package verification on 2026-05-12:

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
- Clean release venv build for the latest package-affecting app code with `$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean`: build completed after the OCR pair-processing slice.
- Global-interpreter `python -m PyInstaller build_app.spec --noconfirm`: failed by design because this machine has `opencv-python==4.10.0.84` and `opencv-contrib-python==4.10.0.84` installed outside the release venv.
- `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --max-package-size-mb 650 --max-startup-seconds 5`: fast OCR-ready smoke passed with package size `596.349 MB`, startup time `2.234` seconds, metadata, no forbidden OpenCV dist-info, and `Ready` state in the report.
- `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5 --min-window-width 1000 --min-window-height 600 --require-clean-exit`: real packaged EasyOCR initialization smoke passed with package size `596.405 MB`, startup time `4.641` seconds, window size `1216x889`, clean GUI exit code `0`, metadata build date `2026-05-12T04:26:44+00:00`, no forbidden OpenCV dist-info, isolated settings file under smoke `APPDATA`, temporary profile cleanup, and `Ready` state in the report.

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
- Run `scripts\check_ocr_evidence_bundle.py` after fixture audit, baseline,
  matrix, and live-comparison reports to prevent dry-run or failed artifacts
  from being treated as promotion evidence.
- Benchmark candidate engines only after fixture baselines exist.
- Continue package-size cleanup only one measured PyInstaller/dependency change
  at a time, with clean build and package smoke after each removal.
- Continue extracting UI panels/dialogs/controller helpers only while targeted
  tests and source/package smoke stay green. `docs/GUI_PARITY_CHECKLIST.md`
  now records dated automated launch/package evidence for the three Python
  entrypoints and built EXE, the canonical source/package smokes enforce the
  `1000x600` minimum window size plus clean GUI exit, and focused unit tests
  cover menu, toolbar, shortcut, source icon, file/folder, Excel, and grid
  parity. The checklist remains broader than those smokes; keep adding manual
  evidence or granular tests before treating every item as a green gate.
