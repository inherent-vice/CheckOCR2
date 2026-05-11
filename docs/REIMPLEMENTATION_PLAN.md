# CheckOCR2 Reimplementation Plan

Date: 2026-05-11

## Purpose

This document defines the implementation plan for rebuilding CheckOCR2's
technical structure while preserving the current GUI features, shortcuts, and
operator workflow. The goal is not a visual redesign. The goal is to make the
program faster, more reliable, more testable, and easier to package without
breaking the current daily-use behavior.

The current app is a working Tkinter OCR automation tool, but the active
implementation is concentrated in `check_capture_ocr.py`. The refactor must be
incremental: freeze existing behavior with tests, split one boundary at a time,
keep both launchers working, and verify the GUI after every meaningful step.

For the latest execution order, verification gates, agent coordination rules,
and commit checklist, use `docs/REIMPLEMENTATION_EXECUTION_GUIDE.md`.

## Non-Negotiable GUI Parity Contract

The following behavior must remain available throughout the migration:

- Window title, icon behavior, initial size, and existing Korean labels.
- Menu bar, toolbar, OCR start/stop buttons, theme selector, and log panel.
- Shortcuts: `F5`, `Esc`, `F1`, `Ctrl+S`, `Ctrl+L`, `Ctrl+O`, grid copy/paste,
  grid delete, and cell edit escape/enter behavior.
- Excel file selection, Excel load, output-folder auto-fill, and output-folder
  open behavior, including UNC/network paths.
- Capture coordinate tools: click point, full area, date area, rate area, and
  area preview overlays.
- Timing controls for paste/load delay.
- Options for detailed image saving, KBP skip, OCR upscaling enablement,
  upscaling factor, and upscaling method.
- Preset save, apply, delete, and persisted current settings.
- Excel grid columns and behaviors: `종목코드`, `종목명`, `날짜`, `금리`, `상태`,
  row add/delete/clear, clipboard paste, selected row copy, selected rate copy,
  context menu, and double-click editing.
- OCR workflow start, stop, row status updates, final export, and `_updated.xlsx`
  output naming.

Any change that affects these items must include a parity check and either a
test or a manual verification note.

## Main Risks And Current Status

- Still open: `check_capture_ocr.py` owns some GUI construction, worker
  lifecycle, and release-compatible controller behavior. WorkController state
  has moved into `checkocr2/work_controller.py`; theme management has moved
  into `checkocr2/ui/theme.py`; overlay windows have moved into
  `checkocr2/ui/overlays.py`; grid data management has moved into
  `checkocr2/data_manager.py`; settings UI binding has moved into
  `checkocr2/ui/settings_binding.py`; current settings load/save/reset actions
  have moved into `checkocr2/ui/settings_actions.py`; preset controller
  behavior has moved into `checkocr2/ui/presets.py`; low-risk panels, menu/toolbar,
  shortcut/about dialogs, Excel load/output-folder actions, coordinate
  capture/preview actions, grid refresh/tag actions, OCR run/stop and
  input-validation actions, options actions, and legacy queue dispatch have
  been extracted incrementally.
- Mitigated: EasyOCR now initializes after the UI appears, on a background
  worker, and OCR start is blocked until the reader is ready.
- Still open: OCR workflow is sequential and uses fixed wait times. Current
  defaults still add about three seconds per row before OCR cost.
- Mitigated: full-area screenshots are captured and saved only when detailed
  image saving is enabled; date/rate crop capture still runs normally.
- Partially mitigated: runtime OCR defaults to `detail=0` for parity, but
  `ocr_detail_level=1` can collect confidence and enforce optional date/rate
  confidence thresholds. Benchmark tooling can also test `detail=1` and field
  allowlists.
- Mitigated: tracked `settings.json` was replaced by `settings.example.json`,
  with runtime settings stored under `%APPDATA%\CheckOCR2\settings.json`.
- Mitigated: output folder cleanup and UNC normalization now use
  `checkocr2/paths.py` instead of the workflow manager.
- Partially mitigated: queue events, rows, and settings have typed seams, but
  legacy tuple dispatch remains at the Tk controller edge. OCR-start validation
  messages, grid status label summaries, grid render value/tag decisions, and
  grid clipboard text generation are now isolated behind tested helpers; legacy
  `grid_update` row mutation is also parsed through `events.py` and tested in
  `table_model.py`, and final-export queue payload validation is typed in
  `events.py`.
- Partially mitigated: broad exception handlers have been narrowed around GUI,
  file, OCR, and export boundaries; remaining broad catches are adapter and
  top-level workflow safety boundaries.
- Partially mitigated: dependency files and build metadata are split, and the
  direct GUI OpenCV dependency was replaced by EasyOCR's required headless
  OpenCV pin. Release-build preflight rejects contaminated GUI/contrib OpenCV
  environments, and package smoke now rejects packaged GUI/contrib OpenCV
  dist-info. PyInstaller hidden imports and OCR-related package size still need
  package-smoke-backed cleanup.
- Mitigated: screen copy/click/paste-wait/screenshot capture logic now lives in
  `checkocr2/capture_adapter.py`, with the legacy manager method reduced to a
  compatibility wrapper.

## Target Architecture

Keep the current public entrypoints:

```text
check_capture_ocr.py                  # stable thin launcher and re-export
Check_Capture_Excel_V6.1_배포.py       # Korean compatibility launcher
```

Move implementation behind them:

```text
checkocr2/
  __init__.py
  main.py                             # main() bootstrap
  app.py                              # CheckCaptureOCRApp shell/controller
  models.py                           # OcrRow, CaptureAreas, Delays, Options
  events.py                           # typed queue/UI event contracts
  settings.py                         # SettingsStore, presets, migration
  paths.py                            # UNC cleanup, output naming, folder open
  logging_config.py                   # logger + Tk queue handler
  data_manager.py                     # Excel grid state and export events
  table_model.py                      # row CRUD, state counts, status rules
  excel_io.py                         # Excel read/write only
  image_processing.py                 # crop validation, upscaling, preprocessing
  ocr_engine.py                       # EasyOCR/RapidOCR/etc adapter boundary
  capture_adapter.py                  # screen copy/click/screenshot capture
  screen_automation.py                # pyautogui and clipboard adapter
  workflow.py                         # OCR orchestration without Tk imports
  worker.py                           # thread/cancel/event bridge
  ui/
    main_window.py
    theme.py
    overlays.py
    coordinate_actions.py              # coordinate capture and preview glue
    folder_actions.py                  # Excel and output-folder UI actions
    dialogs.py
    settings_binding.py
    presets.py
    ocr_actions.py                    # OCR start/stop and input validation glue
    options_actions.py                # options-panel behavior glue
    panels/
      file_panel.py
      coordinates_panel.py
      timing_panel.py
      options_panel.py
      preset_panel.py
      grid_panel.py
      log_panel.py
```

Desired flow:

```text
Tk UI -> App controller -> Worker -> Workflow
Workflow -> ScreenAutomation + OcrEngine + TableModel + ExcelIO
Worker -> typed UiEvent queue -> Tk UI only
```

## Implementation Phases

### Phase 0: Baseline And Safety Net

Objective: capture current behavior before moving code.

Tasks:

- Add a GUI parity checklist under `docs/`.
- Add `pyproject.toml` with scoped `pytest`, `ruff`, and formatting settings.
- Exclude `legacy/`, `build/`, and `dist/` from default lint/format checks.
- Add characterization tests around current behavior before extraction.
- Add test fixtures for settings, sample rows, sample Excel files, and OCR crop
  images.

Validation:

- `python -m compileall check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py`
- `python -m pytest`
- Launch both Python entrypoints.

### Phase 1: Settings, Models, And Typed Events

Objective: make state explicit without changing behavior.

Tasks:

- Add `OcrRow`, `CaptureAreas`, `Delays`, `OcrOptions`, `RunSummary`, and
  `UiEvent` models.
- Replace ad hoc queue payloads with typed event wrappers while preserving
  existing UI handling.
- Move settings logic into `checkocr2/settings.py`.
- Convert tracked `settings.json` into `settings.example.json`.
- Add migration from old repo-local `settings.json` to a per-user local config
  path.

Validation:

- Old settings and presets load without loss.
- New settings save does not mutate source-controlled defaults.
- Tests cover corrupt settings, missing keys, presets, and current settings.

### Phase 2: Pure Logic Extraction

Objective: pull out easy-to-test code first.

Tasks:

- Move UNC/path cleanup and output naming to `paths.py`.
- Move date/rate parsing and validation into a pure parser module or
  `image_processing.py` if kept OCR-adjacent.
- Move upscaling and crop validation into `image_processing.py`.
- Move row CRUD and status finalization into `table_model.py`.
- Move Excel import/export to `excel_io.py`.

Validation:

- Tests cover date formats, rate formats, invalid OCR strings, path cleanup,
  export filename generation, stopped-status blanking, and Korean/English Excel
  headers.
- GUI still loads Excel, edits grid rows, saves settings, and exports the same
  `_updated.xlsx` structure.

### Phase 3: OCR And Automation Boundaries

Objective: make OCR and screen automation replaceable and benchmarkable.

Tasks:

- Add `OcrEngine` interface with an EasyOCR implementation.
- Add `ScreenAutomation` interface wrapping click, paste, screenshot, and crop.
- Move `pyautogui` and `pyperclip` calls into `screen_automation.py`.
- Move EasyOCR reader creation and `readtext` calls into `ocr_engine.py`.
- Support fake OCR and fake screen automation in tests.
- Keep EasyOCR as the default engine until benchmark data proves another engine
  is better.

Validation:

- Fake 3-row workflow test covers success, KBP skip, capture failure, and stop.
- Unit tests never load real EasyOCR models.
- Live smoke still works on 1-2 representative rows.

### Phase 4: Workflow Extraction

Objective: remove business workflow from Tkinter.

Tasks:

- Move row loop, stop handling, OCR orchestration, status transitions, and final
  summary creation to `workflow.py`.
- Ensure `workflow.py` imports no `tkinter` and opens no dialogs.
- Emit typed `UiEvent` values for logs, row updates, errors, completion, and
  stopped state.
- Keep all messagebox display inside UI/dialog code.

Validation:

- Queue event order tests pass.
- GUI grid still updates row-by-row.
- Stop behavior marks pending rows correctly.
- Export still happens only once at finalization.

### Phase 5: Responsiveness And Performance

Objective: improve speed without changing the operator surface.

Tasks:

- Initialize OCR after the window is visible, in a background worker.
- Add explicit UI states: `Starting`, `OCR Loading`, `Ready`, `Running`,
  `Stopping`, `Error`.
- Disable OCR start until the reader is ready.
- Add per-row stage timing: click, paste wait, load wait, capture, preprocess,
  OCR date, OCR rate, parse, update, export.
- Stop saving full-area screenshots unless diagnostics/detail saving is enabled.
- Add run report JSON next to the Excel output with timing, blank fields,
  confidence if available, and failure reasons.
- Only reduce fixed waits after timing logs prove the screen is stable.

Validation:

- App window appears before OCR model initialization completes.
- F5 cannot start before OCR ready.
- Baseline and optimized runs are compared on the same 10-row live smoke.
- No increase in blank or false-positive values.

### Phase 6: OCR Accuracy Benchmark

Objective: make OCR decisions evidence-based.

Tasks:

- Build `tests/fixtures/ocr_crops/` with 100-200 representative date/rate crop
  images.
- Add `ground_truth.csv` with expected normalized values.
- Benchmark current EasyOCR CPU mode first.
- Test upscaling grid: `1.0`, `1.5`, `2.0`, `2.5`, `3.0`.
- Test resampling: `BILINEAR`, `BICUBIC`, `LANCZOS`.
- Test EasyOCR `detail=1` to use confidence.
- Test field-specific allowlists for date and rate if supported cleanly.
- Compare candidates only after baseline exists: RapidOCR, Tesseract, and
  PaddleOCR.

Acceptance criteria:

- Exact normalized date/rate accuracy must not regress.
- Blank fields must decrease or remain unchanged.
- False positives must not increase.
- P95 OCR latency should improve or package size should materially decrease.
- Candidate must pass three consecutive fixture runs.

### Phase 7: Build And Deployment Hardening

Objective: make packaging reproducible and smaller.

Tasks:

- Keep one primary PyInstaller spec.
- Mark the secondary spec as experimental or remove it after proof.
- Split runtime, build, and dev dependencies.
- Add pinned constraints or lock files.
- Remove unused `customtkinter`, `psutil`, and OpenCV only after package smoke
  proves they are not needed.
- Reduce PyInstaller hidden imports based on measured missing-module evidence.
- Add package metadata: version, build date, Python version, dependency hash.
- Add package smoke script that launches the built EXE, waits for the window
  title, verifies OCR-ready state, and exits cleanly.

Validation:

- `$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean`
- `dist/CheckCaptureOCR_V6.1/CheckCaptureOCR_V6.1.exe` launches.
- Window title, icon, settings load, and clean exit verified.
- Package size and startup time recorded, and package smoke enforces the
  approved package size and startup-time budgets.

## Test Strategy

Use TDD for new modules and characterization tests for existing behavior.

Test layers:

1. Characterization tests for current monolith behavior.
2. Unit tests for parsing, settings, paths, models, row status, and Excel naming.
3. Component tests for Excel I/O, OCR engine with fake reader, and automation
   adapter with fake screen/clipboard.
4. Workflow tests using fake OCR and fake automation.
5. GUI smoke tests with EasyOCR, dialogs, file pickers, and threads patched.
6. Package smoke tests for the built EXE.
7. OCR benchmark tests against fixture images and `ground_truth.csv`.

Recommended command after test infrastructure exists:

```powershell
python -m pytest --cov=checkocr2 --cov=check_capture_ocr --cov-branch --cov-report=term-missing --cov-fail-under=80
```

Sample tests:

- `test_clean_date_formats_yyyymmdd_and_yymmdd`
- `test_clean_rate_collapses_comma_middle_dot_and_multiple_decimals`
- `test_clean_folder_path_normalizes_single_backslash_unc_on_windows`
- `test_load_excel_accepts_korean_headers`
- `test_export_grid_writes_expected_sheet_and_blanks_stopped_status`
- `test_capture_screenshots_sanitizes_stock_code_filename`
- `test_extract_text_upscales_image_before_reader_call`
- `test_execute_workflow_skips_kbp_when_enabled`
- `test_execute_workflow_sends_finalize_message_after_success`
- `test_legacy_launcher_constructs_app_and_enters_mainloop`

## Parallel Agent Workstreams

Use parallel agents during implementation only when write scopes are disjoint.

### Architecture Agent

Owns:

- Package layout.
- Migration sequence.
- Entry-point compatibility.
- Module boundary decisions.

Write scope:

- `checkocr2/app.py`
- `checkocr2/main.py`
- `check_capture_ocr.py`
- architecture docs

### Performance/OCR Agent

Owns:

- OCR benchmark harness.
- Timing instrumentation.
- OCR engine comparison plan.
- Capture and preprocessing optimization.

Write scope:

- `checkocr2/ocr_engine.py`
- `checkocr2/image_processing.py`
- `scripts/benchmark_ocr.py`
- `tests/fixtures/ocr_crops/`

### TDD/Test Agent

Owns:

- Test infrastructure.
- Fixtures.
- Characterization tests.
- Workflow fake objects.

Write scope:

- `tests/`
- `pyproject.toml`
- test fixtures

### Python Modernization Agent

Owns:

- Dependency hygiene.
- Ruff/Black/mypy configuration.
- Error hierarchy and logging boundaries.
- Settings path migration.

Write scope:

- `requirements*.txt`
- `pyproject.toml`
- `checkocr2/settings.py`
- `checkocr2/logging_config.py`
- `checkocr2/exceptions.py`

## Commit Sequence

Recommended commit order:

1. `docs: add GUI parity and reimplementation plan`
2. `test: add characterization tests for current OCR helpers`
3. `chore: add pyproject test and lint configuration`
4. `chore: introduce checkocr2 package shell`
5. `refactor: add typed models and UI events`
6. `refactor: extract settings store`
7. `refactor: extract paths and parsing helpers`
8. `refactor: split table model and Excel IO`
9. `refactor: isolate OCR engine and screen automation`
10. `refactor: move OCR workflow out of Tk app`
11. `perf: initialize OCR asynchronously`
12. `perf: add OCR benchmark and timing report`
13. `build: consolidate PyInstaller packaging`
14. `docs: update operator and developer guides`

Each commit must leave the app launchable.

## Global Acceptance Criteria

The reimplementation is successful only if all of these are true:

- Current GUI feature surface is preserved.
- Both Python launchers still work.
- Existing settings and presets migrate.
- OCR start/stop behavior remains predictable.
- Excel import/export output shape remains compatible.
- Offline OCR fixture accuracy is no worse than baseline.
- Startup becomes responsive before OCR model loading completes.
- Runtime settings and logs are no longer committed source state.
- Package build and packaged GUI smoke pass.
- Tests provide enough coverage to continue refactoring safely.
