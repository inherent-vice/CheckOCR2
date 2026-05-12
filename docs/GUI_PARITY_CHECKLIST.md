# GUI Parity Checklist

Use this checklist before and after every reimplementation phase. The goal is
to preserve the current operator workflow while changing the internal
architecture.

## Evidence Status

As of 2026-05-12, this checklist is still only partly automated.
`scripts/source_gui_smoke.py` records repeatable source-launch, Ready-state,
window-title, window-size, clean-exit, and isolated settings-file evidence for Python
entrypoints. `scripts/package_smoke.py` covers the built EXE, package metadata,
real OCR-ready startup, package size, window-size, clean-exit, and isolated
settings-file behavior. The
remaining unchecked items below still need either manual evidence or more
granular automated parity tests before the whole checklist can be treated as a
green gate.

Latest automated evidence:

| Scope | Command | Evidence |
| --- | --- | --- |
| Canonical source launcher | `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45 --min-window-width 1000 --min-window-height 600 --require-clean-exit` | Passed on 2026-05-12 with title `📊 Check Capture OCR V6.1`, `runtime_state="Ready"`, `ocr_ready=true`, startup `1.015s`, window size `1044x788`, and clean GUI exit code `0`. |
| Compatibility launcher | `python scripts\source_gui_smoke.py --entrypoint "python Check_Capture_Excel_V6.1_배포.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45 --min-window-width 1000 --min-window-height 600 --require-clean-exit` | Passed on 2026-05-12 with title `📊 Check Capture OCR V6.1`, `runtime_state="Ready"`, `ocr_ready=true`, startup `1.016s`, window size `1044x788`, and clean GUI exit code `0`. |
| Package bootstrap launcher | `python scripts\source_gui_smoke.py --entrypoint "python -m checkocr2.main" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45 --min-window-width 1000 --min-window-height 600 --require-clean-exit` | Passed on 2026-05-12 with title `📊 Check Capture OCR V6.1`, `runtime_state="Ready"`, `ocr_ready=true`, startup `1.015s`, window size `1044x788`, and clean GUI exit code `0`. |
| Built EXE | `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5 --min-window-width 1000 --min-window-height 600 --require-clean-exit` | Passed on 2026-05-12 with title `📊 Check Capture OCR V6.1`, real OCR `Ready`, package size `596.409 MB`, startup `4.187s`, window size `1044x788`, and clean GUI exit code `0`. |
| Package build and icon resource | `.\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm`; `ExtractAssociatedIcon(dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe)` | Passed on 2026-05-12. Clean venv build completed, PyInstaller copied `eye_ocr_02_scanline.ico` into the EXE, and Windows extracted `.analysis_tmp\packaged_icon_extracted.ico` (766 bytes, SHA256 `8C22D92B3ECB00AA50AFFF27CA4F2792D576B0B2473BB33F802778172325D0F7`). |
| Menu, toolbar, shortcuts, source icon helper | `python -m pytest tests\test_menu.py tests\test_toolbar.py tests\test_keyboard_actions.py tests\test_icons.py --basetemp $env:TEMP\checkocr2-parity-menu-toolbar-shortcuts-icons` | `9 passed` on 2026-05-12. Covers menu cascades and commands, toolbar title/start/stop/theme selector, `F5`, `Esc`, `F1`, `Ctrl+S`, `Ctrl+L`, `Ctrl+O`, and preferred ICO/PNG application. |
| File/folder and grid behavior | `python -m pytest tests\test_folder_actions.py tests\test_excel_table_modules.py tests\test_data_manager.py tests\test_grid_panel.py tests\test_grid_actions.py tests\test_grid_edit_actions.py tests\test_grid_refresh_actions.py --basetemp $env:TEMP\checkocr2-file-grid-parity3` | `61 passed` on 2026-05-12. Covers Excel browse filters, output-folder autofill/browse/open for local and UNC paths, Korean Excel headers, blank Excel cells and NaN values staying empty in grid/export paths, `_updated.xlsx`, `OCR_Results`, grid columns, row add/paste/delete/clear, cell editing, context menu, grid shortcuts, and status tags. |
| Coordinates, options, presets, and workflow gates | `python -m pytest tests\test_coordinate_actions.py tests\test_coordinates_panel.py tests\test_settings_binding.py tests\test_settings_actions.py tests\test_settings_compat.py tests\test_settings_store_lifecycle.py tests\test_options_actions.py tests\test_options_panel.py tests\test_presets.py tests\test_preset_panel.py tests\test_start_validation.py tests\test_workflow_module.py tests\test_workflow_report_finalization.py tests\test_completion_actions.py --basetemp $env:TEMP\checkocr2-coordinate-options-workflow-parity` | `72 passed` on 2026-05-12. Covers coordinate relocation and preview payloads, overlay `Esc`, option persistence, preset save/apply/delete/lifecycle, OCR start validation, KBP skip, processing/stopped events, workflow report finalization, and export completion summaries. |
| Log panel and queue dispatch | `python -m pytest tests\test_log_actions.py tests\test_log_panel.py tests\test_logging_and_main.py tests\test_queue_dispatcher.py --basetemp $env:TEMP\checkocr2-log-core-parity` | `18 passed` on 2026-05-12. Covers `INFO`, `WARNING`, `ERROR`, and `SUCCESS` log-widget insertion, APPDATA rotating file logging, Tk log-handler forwarding, queue dispatch, and log panel construction. |

## Launch And Window

- [x] `python check_capture_ocr.py` opens the app.
- [x] `python Check_Capture_Excel_V6.1_배포.py` opens the app.
- [x] Window title is `📊 Check Capture OCR V6.1`.
- [x] App icon is applied when `eye_ocr_02_scanline.ico` exists.
- [x] Initial geometry remains roughly `1200x850`, with minimum size
  `1000x600`.
- [x] App can close cleanly when no work is running.

## Menus, Toolbar, And Shortcuts

- [x] Menu bar still contains file, settings, preview, run, and help actions.
- [x] Toolbar still shows title, OCR start, stop, and theme selector.
- [x] `F5` starts or stops OCR processing.
- [x] `Esc` stops processing when a run is active.
- [x] `F1` opens shortcut help.
- [x] `Ctrl+S` saves current settings.
- [x] `Ctrl+L` loads last settings.
- [x] `Ctrl+O` loads the selected Excel file into the grid.

## File And Folder Workflow

- [x] Excel browse accepts `.xlsx` and `.xls`.
- [x] Selecting an Excel file auto-fills the output folder.
- [x] Excel load populates grid rows from Korean headers.
- [x] Output folder browse works for local and UNC paths.
- [x] Open output folder works for existing local and UNC paths.
- [x] Export still writes `<input_base>_updated.xlsx`.
- [x] Export sheet remains `OCR_Results`.

## Capture Controls

- [x] Click point selection overlay works and saves coordinates.
- [x] Full area selection overlay works and saves coordinates.
- [x] Date area selection overlay works and saves coordinates.
- [x] Rate area selection overlay works and saves coordinates.
- [x] Area preview shows click point, full area, date area, and rate area.
- [x] Overlay `Esc` closes the overlay without crashing.

## Options And Presets

- [x] Paste delay and loading delay values persist.
- [x] Detailed image saving option persists.
- [x] KBP skip option persists and still marks KBP rows complete with blank
  date/rate values.
- [x] OCR upscaling enablement persists.
- [x] Upscaling factor persists.
- [x] Upscaling method persists.
- [x] Preset save, apply, and delete all work.
- [x] Existing presets migrate and remain selectable.

## Grid Behavior

- [x] Grid columns remain `종목코드`, `종목명`, `날짜`, `금리`, `상태`.
- [x] Add row works.
- [x] Paste from clipboard adds tab-delimited rows.
- [x] Delete selected rows works.
- [x] Clear all works after confirmation.
- [x] Double-click cell editing saves with Enter and cancels with Escape.
- [x] Context menu copy actions work.
- [x] `Ctrl+C`, `Ctrl+V`, and `Delete` shortcuts work on the grid.
- [x] Status tags still visually distinguish processing, completed, and error
  rows.

## OCR Run Behavior

- [x] Start is blocked when no rows are loaded.
- [x] Start is blocked when output folder is invalid.
- [x] Start is blocked until OCR engine is ready.
- [x] Row status changes to processing while a row is active.
- [x] Stop request ends the run and marks remaining rows as stopped.
- [x] Completion summary appears after export.
- [x] Log panel receives OCR, warning, error, and completion messages.
- [ ] A 1-2 row live smoke run can complete without mutating production
  workbooks unexpectedly.

## Packaging Smoke

- [x] Clean release venv PyInstaller build completes.
- [x] `dist/CheckCaptureOCR_V6.1/CheckCaptureOCR_V6.1.exe` opens.
- [x] Packaged window title is correct.
- [x] Packaged icon is correct.
- [x] Packaged app reaches OCR-ready state.
- [x] Packaged app exits cleanly.
