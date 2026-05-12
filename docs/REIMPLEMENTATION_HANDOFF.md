# Reimplementation Handoff

Date: 2026-05-12

## Scope

This handoff summarizes the current CheckOCR2 modernization state. The app must
continue to behave like the existing Tkinter OCR tool while the internals are
split into smaller, testable modules. Treat GUI parity as the release contract:
operators should keep the same buttons, shortcuts, Korean labels, Excel flow,
capture tools, presets, grid behavior, output naming, and stop/final-export
behavior.

For the current execution rules, next safe work slices, agent coordination, and
commit checklist, start with `docs/REIMPLEMENTATION_EXECUTION_GUIDE.md`. For
the Korean parallel-agent plan and workstream split, use
`docs/REIMPLEMENTATION_AGENT_PLAN_KO.md`.

## Current Verified State

- Canonical launchers remain available: `check_capture_ocr.py`,
  `Check_Capture_Excel_V6.1_배포.py`, and `python -m checkocr2.main`.
- Runtime settings are stored under `%APPDATA%\CheckOCR2\settings.json`; the
  repo keeps `settings.example.json` only. Legacy fallback and preset timestamp
  compatibility live in `checkocr2/settings_compat.py`.
- EasyOCR initializes after the GUI appears. OCR start is disabled until the
  app reaches `Ready`.
- Workflow, OCR, Excel, data-manager, table, settings, settings-binding, paths,
  image-processing, OCR reader lifecycle, capture automation, runtime-state, work-controller, theme
  manager, run-report, queue-dispatch, shortcut/about dialogs, overlay windows,
  preset controller, file-dialog path preparation, Excel/output-folder actions,
  coordinate capture/preview actions, grid/context-menu actions, grid-update
  actions, grid-edit actions, grid-refresh/status actions, keyboard actions,
  lifecycle actions, runtime-status actions, settings load/save actions, log
  text actions, OCR initialization/run/stop/input-validation actions, options actions,
  work-completion/export/summary/state-finalization actions, application icons,
  window geometry actions, shared section-frame construction,
  OCR-start validation, file, coordinates, timing,
  options, preset, grid, and log panel seams, the menu bar, top toolbar, and
  main-window layout now have test coverage.
- JSON run reports capture row timing, blank fields, status counts, export
  timing, failure reasons, and optional OCR confidence fields.
- Benchmark tooling exists for OCR crops, matrix sweeps, `detail` mode, and
  field-specific allowlists.
- Package-smoke runtime status payload writing is isolated in
  `checkocr2/package_smoke_status.py`, while the Tk shell only delegates status
  reporting.
- Fixture audit and live run comparison scripts now gate real OCR evidence
  before OCR-default or wait-time changes.
- `scripts/check_ocr_evidence_bundle.py` is the final OCR evidence guard: it
  rejects not-ready audit reports, dry-run or zero-case benchmark artifacts,
  matrix coverage failures, and rejected live comparisons. Matrix regressions
  are warnings by default and become failures with
  `--require-no-matrix-regressions`.
- `scripts/source_gui_smoke.py` now provides repeatable source-launch, Ready,
  window-title, minimum-window-size, clean-exit, isolated `APPDATA`, and
  settings-file smoke evidence for each Python entrypoint.
- Legacy broad exception handling has been reduced to typed catches in
  file/settings/OCR/folder/icon/status paths; remaining broad catches are the
  top-level workflow and adapter safety boundaries.
- Excel and OCR third-party failures are normalized into local exception types
  before reaching the GUI boundary, with tests for corrupt workbooks, Excel
  writer failures, and OCR reader failures.
- Package smoke verifies build metadata, OCR-ready startup, package size,
  startup budget, minimum window size, clean GUI exit, isolated settings-file
  load, and absence of forbidden GUI/contrib OpenCV metadata.
- PyInstaller no longer broadly collects all Torch submodules; targeted Torch
  imports plus PyInstaller's Torch hooks are verified by clean build, fast
  startup smoke, and real packaged EasyOCR initialization smoke. Optional
  TensorFlow, Keras, and TensorBoard stacks are explicitly excluded from the
  bundled package.

Latest code gate result: `ruff` passed, `pytest` passed with 416 tests,
`compileall` passed, benchmark dry-runs passed, and source GUI fast-OCR smoke
reached `Ready` with a `1216x889` window against the `1000x600` minimum gate.
The latest package gate uses the 2026-05-12 clean PyInstaller release build
plus real package smoke at about `596.405 MB` with startup `4.641` seconds,
window size `1216x889`, clean GUI exit code `0`, and settings-file verification
under isolated `APPDATA`.

The current GUI parity verification slice extends source and package smokes to
capture the main Tk window rectangle and request a GUI close through the matched
window handle. Focused script tests and live source/package smoke preserve the
existing startup title, Ready-state, settings-file, package metadata, and real
OCR readiness checks while adding window-size and clean-exit evidence.

The latest GUI parity documentation slice records existing unit-test evidence
for menu cascades and commands, toolbar title/start/stop/theme selector,
keyboard shortcuts, F5 run/stop dispatch, and source icon helper behavior.
`docs/GUI_PARITY_CHECKLIST.md` now marks those items as automated while keeping
packaged icon resource verification and workflow-heavy parity items open.

The latest file/grid parity slice adds explicit tests for Korean Excel headers,
local and UNC output-folder open behavior, `_updated.xlsx` output naming, and
the `OCR_Results` export sheet. The checklist now marks file/folder workflow
and grid behavior items as automated while leaving capture/options/OCR live-run
items open.

The current small model-seam slice widens `OcrRow.from_dict()` from concrete
`dict[str, Any]` input to `Mapping[str, Any]`. This keeps legacy grid dicts
working while making the typed workflow row snapshot compatible with mutable and
read-only mapping rows. Focused verification has passed for `ruff`, `mypy` on
`models.py`/`workflow.py`, and package-helper/workflow tests.

The current OCR extraction slice moves the single-field OCR read sequence into
`checkocr2/ocr_field_extraction.py`. The legacy manager wrapper still owns the
same method name and dependency injection points, while the package helper owns
image-load/preprocess/OCR/parse/total timings, confidence metadata, rejection
warnings, OCR result logs, temp cleanup logs, and blank-field error handling.

The current OCR pair-processing slice moves date/rate image-pair orchestration
into `checkocr2/ocr_pair_processing.py`. The legacy manager wrapper still owns
the same public method, while the package helper preserves call order,
missing-source skips, partial-failure return values, Korean error logs, and
manager monkeypatch compatibility.

The newest structural slices extract coordinate capture/preview action glue
into `checkocr2/ui/coordinate_actions.py` and Excel/output-folder action glue
into `checkocr2/ui/folder_actions.py`. Source gates pass for click-point
relocation, area relocation, preview payloads, folder selection/open behavior,
legacy wrapper delegation, and a fast GUI Ready smoke. Real package smoke was
rerun because `folder_actions.py` is packaged application code.

The source-launch verification slice adds `scripts/source_gui_smoke.py`; it passed for
`python check_capture_ocr.py`, `python Check_Capture_Excel_V6.1_배포.py`, and
`python -m checkocr2.main` with isolated `APPDATA`, `require-ready`, and
`require-settings-file`.

The newest implementation slice moves screen copy/click/paste-wait/screenshot
capture into `checkocr2/capture_adapter.py`; focused capture/workflow tests pass
and the legacy manager wrapper still feeds captured timing into run reports.
Source GUI smoke and real package smoke both pass for this slice.

The grid context-menu structural slice moved grid context-menu construction into
`checkocr2/ui/grid_actions.py`; focused grid tests pass for menu labels,
ordering, command wiring, popup coordinates, and grab cleanup. Source GUI smoke
and real package smoke both pass for this slice.

The log-action structural slice moved log text-widget updates into
`checkocr2/ui/log_actions.py`; focused log tests pass for state transitions,
tag fallback, insert/scroll behavior, and legacy wrapper delegation. Source GUI
smoke and real package smoke both pass for this slice.

The grid-update structural slice moved legacy grid-update queue handling into
`checkocr2/ui/grid_update_actions.py`; focused grid-update tests pass for
scroll/refresh behavior, malformed payload logging, and legacy wrapper
delegation. Source GUI smoke and real package smoke both pass for this slice.

The latest structural slice moved global shortcut binding and F5 dispatch into
`checkocr2/ui/keyboard_actions.py`; focused keyboard tests pass for shortcut
sequences, callback wiring, idle/run F5 behavior, and legacy wrapper
delegation. Source GUI smoke and real package smoke both pass for this slice.

The latest grid editing slice moved double-click cell edit entry creation and
save/cancel/focus-out behavior into `checkocr2/ui/grid_edit_actions.py`;
focused grid-edit tests pass for Tk event binding, theme registration, update
delegation, and legacy wrapper compatibility. Source GUI smoke and real
package smoke both pass for this slice.

The latest grid refresh slice moved Treeview redraw and status/progress label
updates into `checkocr2/ui/grid_refresh_actions.py`; focused refresh tests pass
for delete/insert ordering, render values/tags, label no-op behavior, and
legacy wrapper compatibility. Source GUI smoke and real package smoke both pass
for this slice.

The latest runtime-status slice moved runtime-state button updates,
OCR-ready/error mapping, and package-smoke status writing into
`checkocr2/ui/runtime_status_actions.py`; focused tests pass for smoke env
handling, no-workflow no-op behavior, write failure logging, and legacy wrapper
compatibility. Source GUI smoke and real package smoke both pass for this
slice.

The latest settings-action slice moved current-settings load/save controller
glue into `checkocr2/ui/settings_actions.py`; focused tests pass for saved-path
restore, missing-settings defaults, preset/theme refresh, advanced reset,
quick-save success, error messagebox behavior, and legacy wrapper compatibility.
Source GUI smoke and real package smoke both pass for this slice.

The latest grid-tag styling slice moved Treeview tag color configuration into
`checkocr2/ui/grid_refresh_actions.py`; focused tests pass for tag names, theme
color keys, fallback colors, no-grid no-op behavior, legacy wrapper delegation,
and theme-manager caller compatibility. Source GUI smoke and real package smoke
both pass for this slice.

The latest Excel-load action slice moved grid-load UI glue into
`checkocr2/ui/folder_actions.py`; focused tests pass for missing-file dialog
behavior, DataManager load delegation, zero-row no-op behavior, cleaned output
folder auto-fill, success logs, grid refresh, and legacy wrapper compatibility.
Source GUI smoke and real package smoke both pass for this slice.

The latest OCR input-validation slice moved the remaining start-validation UI
glue into `checkocr2/ui/ocr_actions.py`; focused tests pass for output-folder
trimming, warning/error dialog routing, OCR loading/ready checks, injected
validator behavior, and legacy wrapper compatibility. Source GUI smoke and
real package smoke both pass for this slice.

The latest options-action slice moved OCR upscaling detail show/hide behavior
into `checkocr2/ui/options_actions.py`; focused tests pass for enabled,
disabled, missing-frame, and legacy wrapper delegation paths. Source GUI smoke
and real package smoke both pass for this slice.

The latest completion-summary slice moved OCR completion summary text creation
into `checkocr2/ui/completion_actions.py`; focused tests pin the exact
user-visible multiline summary text and verify both legacy app and workflow
manager wrappers delegate to the shared helper. Source GUI fast-OCR smoke and
real package smoke both pass for this slice.

The latest final-export completion slice moved the shared export/report/dialog
finalization into `checkocr2/ui/completion_actions.py`; focused tests preserve
Excel export fallback naming, run-report row timing/confidence fields, export
timing, report flushing, app-vs-manager reset behavior, grid refresh, and
success/error dialogs. Source GUI fast-OCR smoke and real package smoke both
pass for this slice.

The latest processing-state finalization slice moved the legacy app and
workflow-manager status-finalization wrappers onto a shared
`checkocr2/ui/completion_actions.py` helper backed by the workflow finalizer.
Focused tests preserve stopped-status mutation, success log messages,
malformed-row error logging, and wrapper delegation. Source GUI fast-OCR smoke
and real package smoke both pass for this slice.

The latest lifecycle slice moved app shutdown behavior into
`checkocr2/ui/lifecycle_actions.py`; focused tests preserve idle destruction,
running-work stop requests, worker join timeout, timeout warning, join-error
logging, and legacy wrapper delegation. Source GUI fast-OCR smoke and real
package smoke both pass for this slice.

The latest window action slice moved startup centering into
`checkocr2/ui/window_actions.py`; focused tests preserve update-before-measure
behavior, exact integer-centered geometry, negative offsets for oversized
windows, and legacy wrapper delegation. Source GUI fast-OCR smoke and real
package smoke both pass for this slice.

The latest section-frame slice moved shared styled section construction into
`checkocr2/ui/section_frame.py`; focused tests preserve theme registration,
title label styling, default and fill-parent packing, returned content-frame
behavior, typed host/theme-manager protocol coverage, and positional legacy
wrapper compatibility. Source GUI fast-OCR smoke and real package smoke both
pass for this slice.

The latest OCR preprocessing slice moved reusable image-source loading and
upscaling size/changed-state calculation into `checkocr2/image_processing.py`;
focused tests preserve path input, supported and unknown resampling methods,
success logging only for resized images, warning fallback logging, logger
exception calls, original-object fallback behavior, and legacy path-load
failure re-raise behavior. Source GUI fast-OCR smoke and real package smoke
both pass for this slice.

The latest settings compatibility slice moved `UnifiedSettingsManager` into
`checkocr2/settings_compat.py`; focused tests preserve fallback defaults after
settings load errors and automatic preset `created_at` timestamps. Source and
package smoke both pass for this slice.

The latest OCR field-analysis slice moved date/rate value decisions and legacy
debug-log event text into `checkocr2/ocr_field_analysis.py`; focused tests
preserve empty, whitespace, `None`, valid, and invalid field logs plus
legacy workflow-manager wrapper queue events. The compatibility contract is
now documented in `docs/OCR_FIELD_ANALYSIS_CONTRACT.md`: the helper stays
Tk-free, accepts `raw_text: str | None`, returns
`OcrFieldAnalysis(value, log_events)`, and the manager wrapper only emits
`("log", message, level)` queue events in helper order. Source GUI smoke and
real package smoke both pass for this slice.

The latest OCR initialization slice moved async OCR initialization controller
glue into `checkocr2/ui/ocr_initialization_actions.py`; focused tests preserve
already-initializing and already-ready no-op behavior, package-smoke fast OCR
readiness, real initializer thread launch, failure queue events, and legacy app
wrapper delegation. Source GUI smoke and real package smoke both pass for this
slice.

The latest OCR reader lifecycle slice moved EasyOCR startup and fallback logic
into `checkocr2/ocr_reader_lifecycle.py`; focused tests preserve primary
success, fallback success, legacy settings reset, fatal error messagebox queue
payload, critical log text, and workflow-manager wrapper delegation.
Source GUI smoke and real package smoke both pass for this slice.

The latest OCR runtime-options slice moved `ocr_detail_level` parsing and
field-specific minimum confidence lookup into `checkocr2/ocr_runtime_options.py`;
focused tests preserve the legacy detail-one-only behavior, invalid-value
fallback to `0`, field key construction, and workflow-manager wrapper
delegation. Source GUI smoke and real package smoke both pass for this slice.

The latest OCR temp-cleanup slice moved temporary date/rate crop cleanup
decisions into `checkocr2/image_processing.py`; focused tests preserve
save-detail no-op behavior, date/rate filename matching, non-temp path no-op
behavior, deletion success logs, deletion failure warnings, and workflow-manager
wrapper delegation. Source GUI smoke and real package smoke both pass for this
slice.

The latest OCR workflow run-setup slice moved per-run delays, coordinate
mapping, input-Excel stem detail-image folder selection, save-folder creation,
run-report path, and initial run-report metadata into
`checkocr2/workflow_run_setup.py`; focused tests preserve the helper contract
and the legacy workflow-manager call-site wiring. Source GUI smoke and real
package smoke both pass for this slice.

The latest workflow event-bridge slice moved workflow event forwarding,
`grid_update` parsing, current processing index updates, and row-total timing
into `checkocr2/workflow_event_bridge.py`; focused tests preserve processing,
complete, error, non-grid, and malformed-grid behavior. Source GUI smoke and
real package smoke both pass for this slice.

The latest workflow legacy-adapter slice moved the capture and EasyOCR workflow
adapters into `checkocr2/workflow_legacy_adapters.py`; focused tests preserve
capture arguments, timing copy and `setdefault` semantics, missing-image
behavior, OCR tracking reset, confidence metadata copy semantics, and
`OcrResult` timing identity. Source GUI smoke and real package smoke both pass
for this slice.

The latest workflow report-finalization slice moved success/failure report
finalization into `checkocr2/workflow_report_finalization.py`; focused tests
preserve processing-state finalization, row-report recording, stopped/error
summary values, and report state already finalized at flush time. Source GUI
smoke and real package smoke both pass for this slice.

The latest model compatibility slice widened `OcrRow.from_dict()` to
`Mapping[str, Any]`; the new regression coverage confirms read-only mappings
round-trip into `OcrRow` without requiring a concrete dictionary.

## Commands To Re-Run Before Release

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --min-window-width 1000 --min-window-height 600 --require-clean-exit
python -m venv .analysis_tmp\package_venv
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m pip install -r requirements-build.txt
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5 --min-window-width 1000 --min-window-height 600 --require-clean-exit
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
- Run the OCR evidence bundle gate after audit, baseline, matrix, and live
  comparison artifacts exist.
- Benchmark alternate OCR engines only after the fixture baseline exists.
- Continue trimming PyInstaller hidden imports only when each removal is
  followed by a clean build and package smoke.
- Continue GUI/dialog/worker/controller-helper extraction only while targeted
  tests and source/package smoke stay green. `docs/GUI_PARITY_CHECKLIST.md`
  now records dated automated launch/package evidence for the three Python
  entrypoints and built EXE, but is still broader than those smokes; keep
  adding manual evidence or granular tests before treating every checklist item
  as a green gate.

## Recommended Next Order

1. Build representative date/rate crop fixtures and pass the fixture audit.
2. Record the EasyOCR baseline and matrix reports under `.analysis_tmp/`.
3. Run the 10-row live comparison and save run reports under `.analysis_tmp/`.
4. Run `scripts\check_ocr_evidence_bundle.py` to reject dry-run, zero-case,
   coverage-changed, or rejected live-comparison artifacts.
5. Use `scripts\benchmark_ocr_matrix.py` to compare preprocessing, `detail=1`,
   confidence thresholds, and field allowlists.
6. Tune waits or OCR defaults only if accuracy does not regress.
6. Reduce packaging size through one PyInstaller or dependency change at a time.
7. Add dated parity-checklist evidence for UI areas not covered by source
   smoke.
8. Extract the remaining GUI panels and dialogs in small parity-checked commits.
