# CheckOCR2 Technical Improvement Plan

Date: 2026-05-08

## Executive Summary

CheckOCR2 works as a local Windows/Tkinter OCR automation tool, but the current
implementation is difficult to maintain and expensive to package. The main
risk is not only old dependencies. The larger issue is that GUI construction,
screen automation, OCR, Excel I/O, settings persistence, path handling, and
packaging assumptions are concentrated in one large file.

The safest path is an incremental stabilization-first refactor: preserve the
current operator workflow, add tests and dependency reproducibility, then split
the app into modules behind the existing `check_capture_ocr.py` entrypoint.

## Evidence From Current Repository

- `check_capture_ocr.py` is roughly 2,500 logical lines with 10 classes and 127
  methods.
- `CheckCaptureOCRApp` owns most UI behavior and also coordinates settings,
  queues, OCR startup, Excel operations, dialogs, and worker lifecycle.
- Static scan found 31 broad `except Exception` handlers, 1 bare `except`, 56
  queue message writes, 37 direct messagebox calls, 5 direct `pyautogui` calls,
  and 9 Excel read/write call sites.
- There is no `tests/`, `pyproject.toml`, lock file, formatter config, type
  checker config, CI workflow, or automated package smoke gate.
- Runtime smoke via `Check_Capture_Excel_V6.1_배포.py` opened the GUI. EasyOCR
  CPU initialization took about 28 seconds and the ready process used about
  938 MB working set.
- `settings.json` is tracked and contains machine/operator-specific capture
  coordinates and network paths. This should become local runtime state, not
  repository state.

## Dependency And Packaging Findings

The current dependency file mixes runtime needs, optional build concerns, and
stale comments:

- `customtkinter==5.2.2` is listed but the active app imports only Tkinter.
- `psutil==5.9.6` is listed but not imported by the active app.
- The direct GUI `opencv-python` dependency has been removed; EasyOCR still
  requires `opencv-python-headless`, which remains pinned for the `cv2` module.
- `torch` and `torchvision` are listed as optional but are effectively pulled in
  by EasyOCR packaging. The build spec also collects the full Torch subtree,
  which likely contributes heavily to the large OneDIR package.
- Minimum-only constraints such as `pandas>=1.5.0`, `Pillow>=9.0.0`, and
  `PyInstaller>=5.10.0` are not reproducible. A future install can silently
  change behavior.

PyPI snapshot checked on 2026-05-08:

| Package | Current requirement | PyPI latest seen | Note |
| --- | --- | --- | --- |
| easyocr | `>=1.7.0` | 1.7.2 | Keep short term; benchmark before replacing. |
| customtkinter | `==5.2.2` | 5.2.2 | Remove if not used, or consciously migrate UI. |
| PyInstaller | `>=5.10.0` | 6.20.0 | Pin build tooling separately. |
| psutil | `==5.9.6` | 7.2.2 | Remove unless diagnostics need it. |
| pandas | `>=1.5.0` | 3.0.2 | Pin after Excel regression tests. |
| openpyxl | `>=3.0.0` | 3.1.5 | Pin after workbook fixture tests. |
| Pillow | `>=9.0.0` | 12.2.0 | Pin after image pipeline tests. |
| opencv-python-headless | EasyOCR transitive, pinned | 4.13.0.92 | Keep while EasyOCR remains the default engine. |
| torch | `>=1.13.0` | 2.11.0 | Manage as OCR runtime dependency. |
| torchvision | `>=0.14.0` | 0.26.0 | Include only if actually needed. |

## Key Risks

### 1. Monolithic Architecture

The current file mixes UI state, business rules, file paths, OCR invocation,
automation, and export. This makes small fixes risky because there are no clean
module boundaries or narrow tests.

### 2. Blocking Startup

EasyOCR initializes in `CheckCaptureOCRApp.__init__()` before the UI is fully
usable. On the smoke run, the app became responsive only after the OCR model
finished loading. This should become background lazy initialization with a
visible "OCR ready" state.

### 3. Screen-Coordinate Fragility

The core workflow depends on `pyautogui` clicks, clipboard paste, fixed screen
regions, and timing delays. That is workable for a local operator tool, but it
needs calibration, validation, and better failure evidence.

### 4. Uncontrolled Runtime State

`settings.json` stores local paths and coordinates in the repository. This
creates accidental leakage risk and makes clean installs less predictable.

### 5. Package Bloat And Build Drift

`build_app.spec` is defensive and includes many hidden imports and whole module
trees. This improves survival but makes package size and startup cost worse.
There are two specs with different assumptions, which creates ambiguity.

### 6. No Regression Harness

Core logic such as date/rate cleaning, Excel import/export, path normalization,
row state finalization, and KBP-skip behavior can be tested without live OCR or
GUI automation, but currently is not.

## Improvement Roadmap

## Phase 0: Stabilize Without Behavior Changes

Target: 1-2 days.

Success criteria:

- The app launches from both `check_capture_ocr.py` and
  `Check_Capture_Excel_V6.1_배포.py`.
- Existing operator workflow still works.
- Local settings are no longer treated as source defaults.
- Basic tests cover pure logic.

Tasks:

- Move tracked `settings.json` to `settings.example.json`, add `settings.json`
  to `.gitignore`, and add migration/load fallback behavior.
- Create `pyproject.toml` for formatter, test runner, and project metadata.
- Add `requirements.in` and a generated pinned lock/constraints file.
- Remove clearly unused dependencies first: `customtkinter`, `psutil`, and the
  direct `opencv-python` package. Keep EasyOCR's `opencv-python-headless`
  requirement while EasyOCR remains the active OCR engine.
- Add `tests/` with unit tests for date cleaning, rate cleaning, path cleanup,
  row finalization, and Excel export filename generation.
- Add a non-GUI smoke command that imports the app module without launching the
  Tk root.

## Phase 1: Extract Modules Behind The Same Entry Point

Target: 1 week.

Recommended package layout:

```text
checkocr2/
  __init__.py
  app.py                 # Tk root and app orchestration
  settings.py            # schema, migration, local file handling
  theme.py               # ThemeManager
  data_manager.py        # grid data and Excel I/O
  ocr_engine.py          # EasyOCR reader lifecycle and OCR parsing
  automation.py          # pyautogui and clipboard operations
  paths.py               # UNC/path normalization and output naming
  ui/
    overlays.py
    widgets.py
```

Keep `check_capture_ocr.py` as a thin launcher during the migration. Move one
class at a time and run tests after each move.

Current status update, 2026-05-12: the date/rate OCR field decision logic has
been extracted into `checkocr2/ocr_field_analysis.py`. The pure helper returns
`OcrFieldAnalysis(value, log_events)`, while the legacy workflow manager keeps
emitting the same `("log", message, level)` queue events. The exact value/log
contract is documented in `docs/OCR_FIELD_ANALYSIS_CONTRACT.md`.

## Phase 2: Runtime Performance And Responsiveness

Target: 1-2 weeks.

Tasks:

- Initialize EasyOCR on a background thread after the UI is visible.
- Add explicit states: `Starting`, `OCR Loading`, `Ready`, `Running`,
  `Stopping`, `Error`.
- Disable OCR start until the reader is ready.
- Avoid saving full-area screenshots unless diagnostics are enabled.
- Add a bounded image cache for repeated OCR crops when the same item is
  retried.
- Measure per-row timing: paste wait, screen capture, OCR, parsing, Excel
  export.
- Evaluate whether `detail=0` is sufficient. If confidence gating is required,
  use `detail=1` and store confidence in the row model.

## Phase 3: Build And Deployment Hardening

Target: 3-5 days after modularization.

Tasks:

- Keep one primary PyInstaller spec and remove or rename the secondary spec as
  experimental.
- Replace broad `collect_submodules('torch')` with the smallest verified set
  from a clean package smoke test.
- Add build metadata: app version, build date, Python version, dependency hash.
- Add a package smoke script that launches the built EXE, waits for the window
  title, verifies OCR Ready smoke mode, audits packaged dependency metadata,
  enforces package size and startup-time budgets, then exits cleanly.
- Track package size over time and fail the build if size jumps unexpectedly.

## Phase 4: UI And Operator Workflow

Target: 1-2 weeks.

Tasks:

- Keep Tkinter initially. Do not migrate to CustomTkinter until the core is
  separated; otherwise the UI rewrite will hide business-rule regressions.
- Replace excessive modal dialogs with a persistent status bar and actionable
  error panel.
- Add a calibration screen that validates click point, full area, date area, and
  rate area with a preview before running.
- Add a run summary that lists failed rows with screenshots and reasons.
- Add profile names for different screen layouts or workflows.

## Phase 5: OCR Strategy Review

Target: after fixtures exist.

Do not switch OCR engines first. Build a benchmark harness before deciding.

Benchmark requirements:

- 30-100 representative cropped date/rate images.
- Expected date/rate outputs in a CSV fixture.
- Metrics: accuracy, average latency, P95 latency, memory use, package size.
- Compare current EasyOCR CPU mode, EasyOCR GPU mode if available, and any
  alternate OCR engine only against the same fixture.

## Recommended Execution Order

1. Stop committing local runtime state: `settings.json` migration.
2. Add tests for pure logic and path handling.
3. Clean dependencies and create reproducible install constraints.
4. Split `DataManager`, `settings`, and `paths` first; these are easiest to test.
5. Split `OCRWorkflowManager` into OCR engine and automation layers.
6. Make OCR initialization asynchronous.
7. Harden PyInstaller packaging and package smoke tests.
8. Revisit UI toolkit and OCR engine only after the above is stable.

## Near-Term Backlog

High priority:

- Add `settings.example.json` and ignore local `settings.json`.
- Add `pytest` tests for `_clean_date_text_internal`,
  `_clean_rate_text_internal`, path normalization, and export naming.
- Remove unused `customtkinter`, `psutil`, and OpenCV dependencies if package
  smoke confirms they are not needed.
- Add background OCR initialization.
- Add row-level timing logs.

Medium priority:

- Convert stringly-typed queue messages to small dataclasses or typed named
  tuples.
- Replace broad exception handlers with specific errors at file, OCR, Excel,
  and automation boundaries.
- Create a `RunReport` JSON artifact next to the exported Excel file.
- Add a package size budget and startup time budget.

Low priority:

- Evaluate CustomTkinter or another UI toolkit.
- Add richer export formats.
- Add plugin-style OCR backends.

## Technology Direction

The pragmatic target stack is:

- Python 3.12 or 3.13 only after packaging verification.
- Tkinter retained short term; UI toolkit migration deferred.
- EasyOCR retained short term; alternate OCR engines considered only via
  benchmark.
- `pytest`, `ruff`, and `pyproject.toml` added immediately.
- Pinned dependency constraints generated by `pip-tools` or `uv`.
- PyInstaller 6.x as the only supported packaging path.

## External Version Sources

Package latest-version checks used PyPI JSON metadata on 2026-05-08:

- https://pypi.org/pypi/easyocr/json
- https://pypi.org/pypi/customtkinter/json
- https://pypi.org/pypi/PyInstaller/json
- https://pypi.org/pypi/psutil/json
- https://pypi.org/pypi/pandas/json
- https://pypi.org/pypi/openpyxl/json
- https://pypi.org/pypi/Pillow/json
- https://pypi.org/pypi/opencv-python-headless/json
- https://pypi.org/pypi/torch/json
- https://pypi.org/pypi/torchvision/json
