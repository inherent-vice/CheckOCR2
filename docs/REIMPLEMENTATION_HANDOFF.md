# Reimplementation Handoff

Date: 2026-05-11

## Scope

This handoff summarizes the current CheckOCR2 modernization state. The app must
continue to behave like the existing Tkinter OCR tool while the internals are
split into smaller, testable modules. Treat GUI parity as the release contract:
operators should keep the same buttons, shortcuts, Korean labels, Excel flow,
capture tools, presets, grid behavior, output naming, and stop/final-export
behavior.

For the current execution rules, next safe work slices, agent coordination, and
commit checklist, start with `docs/REIMPLEMENTATION_EXECUTION_GUIDE.md`.

## Current Verified State

- Canonical launchers remain available: `check_capture_ocr.py`,
  `Check_Capture_Excel_V6.1_배포.py`, and `python -m checkocr2.main`.
- Runtime settings are stored under `%APPDATA%\CheckOCR2\settings.json`; the
  repo keeps `settings.example.json` only.
- EasyOCR initializes after the GUI appears. OCR start is disabled until the
  app reaches `Ready`.
- Workflow, OCR, Excel, data-manager, table, settings, settings-binding, paths,
  image-processing, runtime-state, work-controller, theme manager, run-report,
  queue-dispatch, shortcut/about dialogs, overlay windows, preset controller,
  OCR-start validation, and file/coordinates/timing/options/preset/grid/log
  panel seams plus the menu bar, top toolbar, and main-window layout now have
  test coverage.
- JSON run reports capture row timing, blank fields, status counts, export
  timing, failure reasons, and optional OCR confidence fields.
- Benchmark tooling exists for OCR crops, matrix sweeps, `detail` mode, and
  field-specific allowlists.
- Package-smoke runtime status payload writing is isolated in
  `checkocr2/package_smoke_status.py`, while the Tk shell only delegates status
  reporting.
- Fixture audit and live run comparison scripts now gate real OCR evidence
  before OCR-default or wait-time changes.
- Legacy broad exception handling has been reduced to typed catches in
  file/settings/OCR/folder/icon/status paths; remaining broad catches are the
  top-level workflow and adapter safety boundaries.
- Excel and OCR third-party failures are normalized into local exception types
  before reaching the GUI boundary, with tests for corrupt workbooks, Excel
  writer failures, and OCR reader failures.
- Package smoke verifies build metadata, OCR-ready startup, package size,
  startup budget, isolated settings-file load, and absence of forbidden
  GUI/contrib OpenCV metadata.
- PyInstaller no longer broadly collects all Torch submodules; targeted Torch
  imports plus PyInstaller's Torch hooks are verified by clean build, fast
  startup smoke, and real packaged EasyOCR initialization smoke. Optional
  TensorFlow, Keras, and TensorBoard stacks are explicitly excluded from the
  bundled package.

Latest code gate result: `ruff` passed, `pytest` passed with 186 tests,
`compileall` passed, and benchmark dry-runs passed after fixture-audit and live
run-comparison tooling. Latest package gate uses the 2026-05-11 clean
PyInstaller release build for the latest package-affecting app code plus real
package smoke at about `596.372 MB` with startup `4.343` seconds and
settings-file verification under isolated `APPDATA`.

## Commands To Re-Run Before Release

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python -m venv .analysis_tmp\package_venv
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m pip install -r requirements-build.txt
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5
```

Before OCR tuning or release decisions that depend on OCR accuracy, also run
the fixture audit and same-input live comparison commands from
`docs/OCR_BENCHMARK_PLAN.md`; use `docs/OCR_FIXTURE_WORKFLOW.md` to prepare and
promote the audited crop fixtures.

Use the clean release venv for PyInstaller. The global interpreter is expected
to fail release preflight on this machine when GUI/contrib OpenCV packages are
installed outside the release environment.

## Evidence Gates Not Yet Cleared

- Create real OCR crop fixtures under ignored `tests/fixtures/ocr_crops/` with
  a manually reviewed `ground_truth.csv`, then pass the fixture audit script.
- Run a same-input 10-row live OCR comparison through the run-report comparator
  before reducing wait defaults or changing OCR defaults.
- Benchmark alternate OCR engines only after the fixture baseline exists.
- Continue trimming PyInstaller hidden imports only when each removal is
  followed by a clean build and package smoke.
- Continue GUI/dialog/worker/controller-helper extraction only while
  `docs/GUI_PARITY_CHECKLIST.md` and automated tests stay green.

## Recommended Next Order

1. Build representative date/rate crop fixtures and pass the fixture audit.
2. Record the EasyOCR baseline and matrix reports under `.analysis_tmp/`.
3. Run the 10-row live comparison and save run reports under `.analysis_tmp/`.
4. Use `scripts\benchmark_ocr_matrix.py` to compare preprocessing, `detail=1`,
   confidence thresholds, and field allowlists.
5. Tune waits or OCR defaults only if accuracy does not regress.
6. Reduce packaging size through one PyInstaller or dependency change at a time.
7. Extract the remaining GUI panels and dialogs in small parity-checked commits.
