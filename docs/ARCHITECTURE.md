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
- `checkocr2/models.py`: shared column names, status constants, and simple
  data models.
- `checkocr2/events.py`: typed queue/UI event contracts plus legacy
  grid-update and final-export payload parsing.
- `checkocr2/paths.py`: output path generation, UNC normalization, and folder
  helpers.
- `checkocr2/excel_io.py`: Excel import/export logic.
- `checkocr2/table_model.py`: row CRUD, legacy grid-update row mutation,
  clipboard selection text, grid status summaries, and final status
  normalization.
- `checkocr2/ocr_text.py`: OCR date/rate text normalization.
- `checkocr2/image_processing.py`: crop validation and upscaling.
- `checkocr2/ocr_engine.py`: EasyOCR reader/readtext adapter boundary,
  including `detail=1` text/confidence extraction helpers.
- `checkocr2/screen_automation.py`: pyautogui and clipboard wrapper functions.
- `checkocr2/workflow.py`: Tk-free OCR row workflow and report timing support.
- `checkocr2/worker.py`: daemon worker helper.
- `checkocr2/run_report.py`: JSON run report creation/finalization.
- `checkocr2/runtime_state.py`: explicit GUI runtime state to button-state map.
- `checkocr2/build_metadata.py`: release metadata and dependency hash helpers.
- `checkocr2/work_controller.py`: processing run/stop/skip state and stop
  event ownership.
- `checkocr2/ui/theme.py`: Tk/ttk theme catalog, widget registration, and
  theme application for the legacy GUI.
- `checkocr2/ui/menu.py`: menu bar command wiring for files, settings,
  previews, run controls, and help.
- `checkocr2/ui/toolbar.py`: top toolbar with OCR start/stop controls and
  theme selection.
- `checkocr2/ui/dialogs.py`: keyboard-shortcut and about dialogs, including
  build metadata text.
- `checkocr2/ui/queue_dispatcher.py`: legacy Tk queue message dispatch for
  logs, dialogs, grid updates, OCR-ready state, and final export completion.
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
Workflow -> queue events -> Tk app -> grid/log/dialog updates
Tk app -> Excel export -> run report finalization
```

The GUI initializes first, then EasyOCR loads asynchronously. OCR start remains
disabled until the reader is ready. This keeps startup responsive even when
model loading is slow.

Package smoke tests set `CHECKOCR2_PACKAGE_SMOKE_STATUS_FILE=<path>` and wait
for `Ready`. Fast startup smoke also sets `CHECKOCR2_PACKAGE_SMOKE_FAST_OCR=1`
to bypass model loading; real package smoke omits that flag so packaged
EasyOCR initialization is exercised. These environment variables are for smoke
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
