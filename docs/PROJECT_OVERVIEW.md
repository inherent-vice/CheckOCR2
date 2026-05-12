# Project Overview

## Purpose

CheckOCR2 automates a repetitive OCR workflow on Windows:

1. Load stock/code rows from Excel.
2. Copy each code into an external target screen.
3. Capture configured date and rate regions.
4. Run EasyOCR and normalize the extracted values.
5. Update the grid and export an `_updated.xlsx` workbook.
6. Write a JSON run report for timing and failure analysis.

The project is being modernized without changing the current Tkinter GUI
workflow that operators already use.

## Main User Workflow

- Select an input Excel workbook.
- Confirm or adjust the output folder.
- Load rows into the grid.
- Configure click point and capture areas when needed.
- Start OCR with `F5` or the toolbar button.
- Stop with `Esc`, `F5`, or the stop button.
- Review grid statuses, exported Excel output, and run report JSON.

## Current Implementation

`check_capture_ocr.py` remains the canonical GUI implementation. It keeps the
menus, toolbar, grid, dialogs, shortcuts, and compatibility behavior. Reusable
logic is extracted into `checkocr2/` modules so each seam can be tested without
loading the full GUI.

The old release filename, `Check_Capture_Excel_V6.1_배포.py`, now delegates to
the package bootstrap and remains available for existing shortcuts.

## Important Modules

- `settings.py`: per-user JSON settings under `%APPDATA%\CheckOCR2`.
- `excel_io.py`: Excel read/write behavior.
- `table_model.py`: grid row and status rules.
- `ocr_text.py`: date and rate normalization.
- `image_processing.py`: crop validation and image upscaling.
- `ocr_engine.py`: EasyOCR adapter boundary.
- `screen_automation.py`: pyautogui and clipboard wrappers.
- `workflow.py`: row processing workflow outside Tkinter.
- `worker.py`: background thread helper.
- `run_report.py`: JSON timing/error report writer.
- `runtime_state.py`: explicit GUI start/stop/OCR readiness state.
- `build_metadata.py`: package metadata and dependency hash generation.
- `ui/`: extracted Tk panels, dialogs, overlays, action helpers, menu/toolbar,
  and queue-dispatch seams.

## Documentation Map

- `README.md`: quick start, commands, repo map, evidence gates.
- `docs/ARCHITECTURE.md`: module boundaries and runtime flow.
- `docs/MODERNIZATION_PLAN_KO.md`: Korean modernization execution summary,
  OCR evidence gates, and next implementation order.
- `docs/REIMPLEMENTATION_STATUS_KO.md`: Korean current-state document for the
  verified baseline, GUI parity contract, OCR gates, next order, and commands.
- `docs/REIMPLEMENTATION_AGENT_PLAN_KO.md`: Korean parallel-agent
  reimplementation plan, workstream split, GUI contract, and evidence gates.
- `docs/REIMPLEMENTATION_PLAN.md`: phased modernization roadmap.
- `docs/REIMPLEMENTATION_EXECUTION_GUIDE.md`: current execution rules,
  next safe slices, parity gates, and commit checklist.
- `docs/REIMPLEMENTATION_HANDOFF.md`: current verified state, release gates,
  and next implementation order.
- `docs/IMPLEMENTATION_STATUS.md`: completed work and remaining gates.
- `docs/GUI_PARITY_CHECKLIST.md`: manual parity checklist before UI changes.
- `docs/OCR_BENCHMARK_PLAN.md`: fixture, benchmark, and matrix-sweep plan.
- `docs/RUN_REPORT.md`: JSON report schema and usage.

## Known Constraints

- OCR tuning requires real crop fixtures, fixture audit, matrix benchmark
  evidence, and a same-input live comparison.
- Desktop automation depends on screen coordinates and the external target app.
- Tests should fake OCR and screen automation unless running an explicit smoke.
- Personal settings, screenshots, production workbooks, and benchmark crops must
  stay out of git.
- Build metadata and package smoke output are evidence, not substitutes for real
  OCR fixture/live-run accuracy checks.
