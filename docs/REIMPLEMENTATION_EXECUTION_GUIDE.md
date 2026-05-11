# Reimplementation Execution Guide

Date: 2026-05-11

## Purpose

Use this guide when continuing the CheckOCR2 modernization work. The goal is to
keep the current Tkinter GUI and operator workflow intact while moving behavior
out of `check_capture_ocr.py` into tested package modules.

This is an execution guide, not a replacement for
`docs/REIMPLEMENTATION_PLAN.md`. The plan describes the long-term roadmap; this
document describes how to continue safely from the current state.

## Current Baseline

- The supported launch paths are `python check_capture_ocr.py`, the
  compatibility release launcher, and `python -m checkocr2.main`.
- Runtime settings live in `%APPDATA%\CheckOCR2\settings.json`; repository
  defaults live in `settings.example.json`.
- EasyOCR loads asynchronously after the Tk window appears. OCR start must stay
  blocked until the app reaches `Ready`.
- Workflow, settings, paths, Excel I/O, OCR engine access, screen automation,
  capture automation, table behavior, run reports, runtime state, worker
  helpers, queue dispatch, start validation, menu/toolbar, dialogs, file-dialog path preparation,
  Excel/output-folder actions, coordinate capture/preview actions, grid
  actions, OCR run/stop actions, work-completion actions, several panels, and
  work-control state now have package-level seams and tests.
- `check_capture_ocr.py` still owns the remaining Tk shell, some controller
  glue, and release-compatible behavior.

## Implementation Rules

- Preserve GUI parity first. Do not change labels, shortcuts, grid behavior,
  export naming, stop behavior, or preset/settings behavior as part of a
  structural refactor.
- Move one boundary at a time. A good commit should extract one helper, panel,
  parser, adapter, or controller seam and prove parity with focused tests.
- Keep the legacy launcher thin and working. Do not remove the old filename
  until a release migration explicitly replaces it.
- Keep OCR decisions evidence-based. Do not change OCR defaults, waits,
  confidence thresholds, or engines without fixture and live-run proof.
- Keep desktop automation local. Do not add external OCR, telemetry, or cloud
  services unless explicitly requested.
- Ignore unrelated dirty files. In this repo, untracked design artifacts or
  local settings should not be staged unless the task is specifically about
  them.

## Next Safe Work Slices

1. Build real OCR fixtures under ignored `tests/fixtures/ocr_crops/` and add
   `ground_truth.csv`. Run the fixture audit before recording a baseline.
2. Record the current EasyOCR baseline and matrix reports under
   `.analysis_tmp/`.
3. Create candidate runs for waits, preprocessing, `detail=1`, confidence
   thresholds, field allowlists, or OCR backends without changing defaults.
4. Run a same-input 10-row live OCR comparison between baseline and candidate
   run reports.
5. Adopt or promote a candidate only after fixture and live comparison evidence
   shows no output regression and a speed or package-size gain.
6. Continue package-size cleanup one measured PyInstaller/dependency change at
   a time, followed by a clean build and package smoke.
7. Continue small controller extractions that do not alter UI layout. Good
   targets are remaining status/update helpers and final controller-only
   branches that can be tested with fakes.

## OCR Accuracy And Speed Gate

Before adopting any OCR or timing change, produce the fixture and benchmark
evidence first:

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json
python scripts\benchmark_ocr.py --output-json .analysis_tmp\easyocr_baseline.json
python scripts\benchmark_ocr_matrix.py --allowlist-modes none,field --output-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json
```

For wait-time or live-speed candidates, also require the same-input live P95
threshold:

```powershell
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --require-p95-improvement --min-p95-improvement-percent 10 --output-json .analysis_tmp\live_ocr_compare.json
```

Accept a candidate only when normalized date/rate accuracy does not regress,
blank-on-expected-nonempty errors do not increase, false positives do not
increase, failure rows do not increase, and either benchmark `p95_latency_ms` or
same-input live P95 row timing improves by at least 10%. For package-driven
OCR/backend changes, package smoke may satisfy the improvement requirement only
when `package_size_mb` drops by a predeclared threshold or at least 25 MB. The
result must hold across three consecutive fixture runs. Review
`field_summaries`, matrix `field_comparisons`, and `coverage_unchanged` so a
date regression or missing field coverage cannot be hidden by a rate
improvement. Accuracy-only candidates can be recorded for manual review, but
should not become defaults without explicit approval.

## GUI Parity Protocol

Use `docs/GUI_PARITY_CHECKLIST.md` before and after UI-moving changes. For
changes that touch startup, threading, Tk state, queue dispatch, packaging, or
EasyOCR initialization, run a source GUI smoke and record the result in
`docs/IMPLEMENTATION_STATUS.md`.

Repeatable source smoke command shape:

```powershell
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file
python scripts\source_gui_smoke.py --entrypoint "python Check_Capture_Excel_V6.1_배포.py" --isolated-appdata --require-ready --require-settings-file
python scripts\source_gui_smoke.py --entrypoint "python -m checkocr2.main" --isolated-appdata --require-ready --require-settings-file
```

Minimum source gate before pushing a structural change:

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file
```

Package-affecting changes must also pass a clean PyInstaller build and
`scripts\package_smoke.py` with real OCR readiness:

```powershell
python -m venv .analysis_tmp\package_venv
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m pip install -r requirements-build.txt
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5
```

## Parallel Agent Protocol

For the Korean operator-facing version of this split, use
`docs/REIMPLEMENTATION_AGENT_PLAN_KO.md`.

Use parallel agents only when write scopes are disjoint or when they are doing
read-only review. Suggested workstreams:

- Architecture: entrypoints, controller seams, module boundaries, docs.
- OCR/performance: fixtures, benchmark matrix, run-report comparison, timing.
- TDD: characterization tests, fake OCR/screen adapters, GUI parity tests.
- Packaging: dependency pins, PyInstaller spec, package smoke, metadata.

Workers must not revert each other's edits. Each worker should report changed
paths, verification commands, and unresolved risks. The coordinating agent
integrates one slice at a time and reruns the repo gate after integration.

## Commit Checklist

Before committing:

- Confirm `git status --short` and stage only intended files.
- Confirm no production spreadsheets, screenshots, raw crop fixtures, local
  settings, benchmark reports, or `.analysis_tmp/` artifacts are staged.
- Use focused messages such as `refactor: extract work controller`,
  `test: add OCR fixture audit`, or `docs: update reimplementation handoff`.
- Update `docs/IMPLEMENTATION_STATUS.md` when a gate, module boundary, package
  result, or remaining evidence requirement changes.

## Stop Conditions

Pause before implementation if a change would alter the visible operator
workflow, require production data, depend on a live external service, or make
OCR behavior less accurate without fixture/live evidence.
