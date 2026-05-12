# GUI Parity Checklist

Use this checklist before and after every reimplementation phase. The goal is
to preserve the current operator workflow while changing the internal
architecture.

## Evidence Status

As of 2026-05-12, this checklist is still only partly automated.
`scripts/source_gui_smoke.py` records repeatable source-launch, Ready-state,
window-title, window-size, and isolated settings-file evidence for Python
entrypoints. `scripts/package_smoke.py` covers the built EXE, package metadata,
real OCR-ready startup, package size, window-size, and isolated settings-file
behavior. The
remaining unchecked items below still need either manual evidence or more
granular automated parity tests before the whole checklist can be treated as a
green gate.

Latest automated evidence:

| Scope | Command | Evidence |
| --- | --- | --- |
| Canonical source launcher | `python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45 --min-window-width 1000 --min-window-height 600` | Passed on 2026-05-12 with title `📊 Check Capture OCR V6.1`, `runtime_state="Ready"`, `ocr_ready=true`, startup `1.032s`, and window size `1216x889`. |
| Compatibility launcher | `python scripts\source_gui_smoke.py --entrypoint "python Check_Capture_Excel_V6.1_배포.py" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45` | Passed on 2026-05-12 with title `📊 Check Capture OCR V6.1`, `runtime_state="Ready"`, `ocr_ready=true`, and startup `1.016s`. |
| Package bootstrap launcher | `python scripts\source_gui_smoke.py --entrypoint "python -m checkocr2.main" --isolated-appdata --require-ready --require-settings-file --timeout 45 --ocr-ready-timeout 45` | Passed on 2026-05-12 with title `📊 Check Capture OCR V6.1`, `runtime_state="Ready"`, `ocr_ready=true`, and startup `1.016s`. |
| Built EXE | `python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5 --min-window-width 1000 --min-window-height 600` | Passed on 2026-05-12 with title `📊 Check Capture OCR V6.1`, real OCR `Ready`, package size `596.404 MB`, startup `1.657s`, and window size `1216x889`. |

## Launch And Window

- [x] `python check_capture_ocr.py` opens the app.
- [x] `python Check_Capture_Excel_V6.1_배포.py` opens the app.
- [x] Window title is `📊 Check Capture OCR V6.1`.
- [ ] App icon is applied when `eye_ocr_02_scanline.ico` exists.
- [x] Initial geometry remains roughly `1200x850`, with minimum size
  `1000x600`.
- [ ] App can close cleanly when no work is running.

## Menus, Toolbar, And Shortcuts

- [ ] Menu bar still contains file, settings, preview, run, and help actions.
- [ ] Toolbar still shows title, OCR start, stop, and theme selector.
- [ ] `F5` starts or stops OCR processing.
- [ ] `Esc` stops processing when a run is active.
- [ ] `F1` opens shortcut help.
- [ ] `Ctrl+S` saves current settings.
- [ ] `Ctrl+L` loads last settings.
- [ ] `Ctrl+O` loads the selected Excel file into the grid.

## File And Folder Workflow

- [ ] Excel browse accepts `.xlsx` and `.xls`.
- [ ] Selecting an Excel file auto-fills the output folder.
- [ ] Excel load populates grid rows from Korean headers.
- [ ] Output folder browse works for local and UNC paths.
- [ ] Open output folder works for existing local and UNC paths.
- [ ] Export still writes `<input_base>_updated.xlsx`.
- [ ] Export sheet remains `OCR_Results`.

## Capture Controls

- [ ] Click point selection overlay works and saves coordinates.
- [ ] Full area selection overlay works and saves coordinates.
- [ ] Date area selection overlay works and saves coordinates.
- [ ] Rate area selection overlay works and saves coordinates.
- [ ] Area preview shows click point, full area, date area, and rate area.
- [ ] Overlay `Esc` closes the overlay without crashing.

## Options And Presets

- [ ] Paste delay and loading delay values persist.
- [ ] Detailed image saving option persists.
- [ ] KBP skip option persists and still marks KBP rows complete with blank
  date/rate values.
- [ ] OCR upscaling enablement persists.
- [ ] Upscaling factor persists.
- [ ] Upscaling method persists.
- [ ] Preset save, apply, and delete all work.
- [ ] Existing presets migrate and remain selectable.

## Grid Behavior

- [ ] Grid columns remain `종목코드`, `종목명`, `날짜`, `금리`, `상태`.
- [ ] Add row works.
- [ ] Paste from clipboard adds tab-delimited rows.
- [ ] Delete selected rows works.
- [ ] Clear all works after confirmation.
- [ ] Double-click cell editing saves with Enter and cancels with Escape.
- [ ] Context menu copy actions work.
- [ ] `Ctrl+C`, `Ctrl+V`, and `Delete` shortcuts work on the grid.
- [ ] Status tags still visually distinguish processing, completed, and error
  rows.

## OCR Run Behavior

- [ ] Start is blocked when no rows are loaded.
- [ ] Start is blocked when output folder is invalid.
- [ ] Start is blocked until OCR engine is ready.
- [ ] Row status changes to processing while a row is active.
- [ ] Stop request ends the run and marks remaining rows as stopped.
- [ ] Completion summary appears after export.
- [ ] Log panel receives OCR, warning, error, and completion messages.
- [ ] A 1-2 row live smoke run can complete without mutating production
  workbooks unexpectedly.

## Packaging Smoke

- [ ] `python -m PyInstaller build_app.spec` completes.
- [x] `dist/CheckCaptureOCR_V6.1/CheckCaptureOCR_V6.1.exe` opens.
- [x] Packaged window title is correct.
- [ ] Packaged icon is correct.
- [x] Packaged app reaches OCR-ready state.
- [ ] Packaged app exits cleanly.
