# Architecture

## Current Shape

CheckOCR2 is still centered on `check_capture_ocr.py`, which owns the Tkinter
window, menus, panels, grid, dialogs, and release-compatible behavior. The
refactor extracts stable, testable seams into `checkocr2/` without removing the
existing GUI surface.

The intended direction is an incremental split, not a rewrite. Every extraction
must keep the canonical launcher, compatibility launcher, and package launcher
working.

## Package Modules

- `checkocr2/main.py` and `checkocr2/app.py`: bootstrap helpers that preserve
  import and launch compatibility.
- `checkocr2/settings.py`: per-user settings store and migration from old
  repo-local settings.
- `checkocr2/settings_compat.py`: legacy `UnifiedSettingsManager` adapter for
  fallback defaults and preset timestamp compatibility.
- `checkocr2/models.py`: shared column names, status constants, and simple
  data models.
- `checkocr2/events.py`: typed queue/UI event contracts plus legacy
  grid-update and final-export payload parsing.
- `checkocr2/paths.py`: output path generation, UNC normalization, and folder
  helpers.
- `checkocr2/excel_io.py`: Excel import/export logic.
- `checkocr2/data_manager.py`: legacy grid data manager for Excel load/export,
  clipboard paste, row deletion, and queue events.
- `checkocr2/table_model.py`: row CRUD, legacy grid-update row mutation,
  clipboard selection text, grid render values/tags, grid status summaries, and
  final status normalization.
- `checkocr2/ocr_text.py`: OCR date/rate text normalization.
- `checkocr2/ocr_field_analysis.py`: pure date/rate OCR field value decisions
  and legacy debug-log event text. It returns `OcrFieldAnalysis(value,
  log_events)` and stays Tk-free; the legacy workflow manager only converts
  those log events into `("log", message, level)` queue events.
- `checkocr2/image_processing.py`: crop validation, pure image upscaling,
  reusable image-source loading/upscale result metadata, and temporary date/rate
  crop cleanup decisions for OCR preprocessing helpers.
- `checkocr2/ocr_engine.py`: EasyOCR reader/readtext adapter boundary,
  including `detail=1` text/confidence extraction helpers.
- `checkocr2/ocr_reader_lifecycle.py`: EasyOCR reader startup lifecycle,
  including English/CPU defaults, fallback reinitialization, legacy settings
  reset, fatal error messagebox queueing, and logger text compatibility.
- `checkocr2/ocr_runtime_options.py`: runtime OCR option interpretation for
  `ocr_detail_level` and field-specific minimum confidence settings.
- `checkocr2/capture_adapter.py`: screen-copy, click, paste-wait, screenshot,
  crop-save, and capture timing orchestration for date/rate OCR images.
- `checkocr2/screen_automation.py`: pyautogui and clipboard wrapper functions.
- `checkocr2/workflow.py`: Tk-free OCR row workflow and report timing support.
- `checkocr2/worker.py`: daemon worker helper.
- `checkocr2/run_report.py`: JSON run report creation/finalization.
- `checkocr2/workflow_run_setup.py`: per-run delay, coordinate, detail-image
  folder, and run-report setup for the legacy OCR workflow manager.
- `checkocr2/runtime_state.py`: explicit GUI runtime state to button-state map.
- `checkocr2/build_metadata.py`: release metadata and dependency hash helpers.
- `checkocr2/work_controller.py`: processing run/stop/skip state and stop
  event ownership.
- `checkocr2/ui/completion_actions.py`: main-thread work completion,
  processing-state finalization, final-export completion, and stopped-work UI
  finalization, including controller reset, runtime-state restore, grid
  refresh, settings save, OCR completion summary text creation, run-report
  finalization, export result dialogs, stopped-state finalization, and stopped
  dialog display.
- `checkocr2/ui/coordinate_actions.py`: click-point relocation, rectangle-area
  relocation, and current-area preview creation for the legacy coordinate
  controls.
- `checkocr2/ui/theme.py`: Tk/ttk theme catalog, widget registration, and
  theme application for the legacy GUI.
- `checkocr2/ui/overlays.py`: full-screen capture and area-preview overlay
  windows for click point and rectangle selection.
- `checkocr2/ui/menu.py`: menu bar command wiring for files, settings,
  previews, run controls, and help.
- `checkocr2/ui/presets.py`: preset combo refresh, apply, save, and delete
  controller logic.
- `checkocr2/ui/toolbar.py`: top toolbar with OCR start/stop controls and
  theme selection.
- `checkocr2/ui/window_actions.py`: window geometry helpers, including
  legacy integer-centered startup positioning.
- `checkocr2/ui/dialogs.py`: keyboard-shortcut and about dialogs, including
  build metadata text.
- `checkocr2/ui/file_dialogs.py`: file/open-folder dialog path preparation,
  including input-file parent output defaults and UNC initial-directory
  fallback behavior.
- `checkocr2/ui/folder_actions.py`: Excel-file selection, output-folder
  selection, Excel grid loading, and output-folder opening across Windows,
  macOS, Linux, and UNC network paths.
- `checkocr2/ui/grid_actions.py`: grid button, context-menu, and clipboard
  actions for add, paste, delete, clear, copy rows, and copy rates while
  preserving Tk messagebox, menu, and clipboard behavior.
- `checkocr2/ui/grid_edit_actions.py`: double-click cell edit entry creation,
  save-on-enter/focus-out, escape cancellation, theme registration, and legacy
  wrapper-compatible event binding.
- `checkocr2/ui/grid_refresh_actions.py`: Treeview status-tag styling,
  row redraw, and grid status/progress label updates using shared table-model
  render helpers.
- `checkocr2/ui/grid_update_actions.py`: legacy grid-update queue handling for
  row mutation delegation, scroll-to-row, refresh, debug logging, and malformed
  payload logging.
- `checkocr2/ui/icons.py`: application icon candidate selection and Tk icon
  application.
- `checkocr2/ui/keyboard_actions.py`: global shortcut binding and F5
  run/stop dispatch for the legacy Tk shell.
- `checkocr2/ui/lifecycle_actions.py`: app shutdown behavior for idle and
  running OCR sessions, including stop request, worker join, timeout warning,
  join-error logging, and final window destruction.
- `checkocr2/ui/log_actions.py`: log text-widget state, tag fallback, insert,
  scroll, and disabled-state restoration behavior.
- `checkocr2/ui/main_window.py`: top-level Tk window layout assembly for the
  menu, toolbar, three-panel grid, and log handler wiring.
- `checkocr2/ui/ocr_initialization_actions.py`: async OCR initialization
  orchestration for the Tk shell, including already-initializing no-op
  behavior, package-smoke fast OCR readiness, real initializer thread launch,
  and legacy `ocr_ready` queue events.
- `checkocr2/ui/ocr_actions.py`: OCR run/stop button orchestration and
  OCR-start input-validation UI dispatch, including validator handoff,
  warning/error messagebox selection, runtime-state transition, worker launch,
  and queued stop logging.
- `checkocr2/ui/options_actions.py`: options-panel behavior for showing or
  hiding OCR upscaling detail controls and persisting advanced settings.
- `checkocr2/ui/queue_dispatcher.py`: legacy Tk queue message dispatch for
  logs, dialogs, grid updates, OCR-ready state, and final export completion.
- `checkocr2/ui/runtime_status_actions.py`: runtime-state button updates,
  OCR-ready state mapping, and package-smoke status payload writing for the Tk
  shell.
- `checkocr2/ui/section_frame.py`: shared styled section-frame construction
  for legacy panel builders, including theme registration, title label styling,
  fill-parent packing, and returning the content frame.
- `checkocr2/ui/settings_actions.py`: current settings load/save controller
  actions, including saved-path restoration, advanced defaults, preset refresh,
  theme restore, advanced reset, and quick-save error reporting.
- `checkocr2/ui/settings_binding.py`: settings-to-Tk-variable mapping for
  current settings, preset application, and advanced option persistence.
- `checkocr2/ui/start_validation.py`: OCR-start validation messages for empty
  grid, invalid output folder, OCR loading, and OCR initialization failure.
- `checkocr2/ui/panels/file_panel.py`: left-side Excel input and output-folder
  panel builder.
- `checkocr2/ui/panels/coordinates_panel.py`: capture coordinate and area
  selection panel builder.
- `checkocr2/ui/panels/timing_panel.py`: paste/load delay panel builder.
- `checkocr2/ui/panels/options_panel.py`: detailed image, KBP skip, and OCR
  upscaling option panel builder.
- `checkocr2/ui/panels/preset_panel.py`: preset load/apply/delete/save panel
  builder.
- `checkocr2/ui/panels/grid_panel.py`: central Excel row grid, scrollbars,
  row-control buttons, key bindings, and status-label panel builder.
- `checkocr2/ui/panels/log_panel.py`: right-side log panel builder.

## Runtime Flow

```text
Tk app -> WorkController -> worker thread -> OCRWorkflowManager/WorkflowRunner
Workflow -> screen automation -> screenshots -> preprocessing -> OCR engine
OCR text -> field analysis -> legacy log/value queue events
Workflow -> queue events -> Tk app -> grid/log/dialog updates
Tk app -> Excel export -> run report finalization
```

The GUI initializes first, then EasyOCR loads asynchronously. OCR start remains
disabled until the reader is ready. This keeps startup responsive even when
model loading is slow. The Tk shell delegates this initialization handoff to
`checkocr2/ui/ocr_initialization_actions.py`.

Package smoke tests set `CHECKOCR2_PACKAGE_SMOKE_STATUS_FILE=<path>` and wait
for `Ready`. Fast startup smoke also sets `CHECKOCR2_PACKAGE_SMOKE_FAST_OCR=1`
to bypass model loading; real package smoke omits that flag so packaged
EasyOCR initialization is exercised. The app writes that payload through
`checkocr2/package_smoke_status.py`. These environment variables are for smoke
automation only and are not part of the normal operator workflow.

## UI Runtime States

The GUI uses `RuntimeState` to keep the start/stop buttons predictable:

- `Starting`: app is constructing the UI.
- `OCR Loading`: EasyOCR is initializing in the background.
- `Ready`: OCR can be started.
- `Running`: OCR worker is active; F5/stop requests cancellation.
- `Stopping`: cancellation was requested and the worker is draining.
- `Error`: OCR engine initialization failed.

Export failures are reported as export errors but return the GUI to the OCR
ready state when the OCR reader is still available.

## Data And Reports

The grid is loaded from Excel and exported to `<input_stem>_updated.xlsx`.
Each run also writes `<input_stem>_run_report.json` with row status, blank
fields, timing, optional OCR confidence fields, export information, and error
details. The report is the primary evidence source for future speed tuning.

Packaged releases include `checkocr2/build_metadata.json`. It records app
version, build date, Python version, direct dependency versions, and a dependency
hash so package smoke output can be tied to a reproducible build environment.

## Testing Boundaries

Unit tests should avoid real EasyOCR, desktop automation, and dialogs unless the
test is explicitly a smoke check. Prefer fake readers, fake screenshots, fake
clipboard/screen functions, and direct queue inspection.

Use `docs/GUI_PARITY_CHECKLIST.md` before UI-moving changes, and keep
`docs/REIMPLEMENTATION_PLAN.md` as the migration roadmap.

The date/rate field-analysis compatibility contract is documented in
`docs/OCR_FIELD_ANALYSIS_CONTRACT.md`.
