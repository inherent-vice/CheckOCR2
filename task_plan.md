# Task Plan: CheckOCR2 PaddleOCR Production Readiness

## Goal

Make CheckOCR2 production-ready for daily CouponCheck operation by adding
PaddleOCR 3.5.0 / PP-OCRv5 as the validated default OCR candidate while
preserving the current GUI workflow and retaining EasyOCR as baseline/fallback.

## Ranked Uncertainties

1. PaddleOCR 3.5.0 runtime/install reliability on this Windows/Python machine.
2. PaddleOCR result shape compatibility with the existing date/rate OCR contract.
3. Whether historical full-area PNGs can produce reproducible date/rate crops.
4. Whether Paddle improves real CouponCheck accuracy and p95 latency.
5. Whether packaged EXE size/startup remains acceptable with Paddle dependencies.

## Phases

| Phase | Status | Success Criteria |
| --- | --- | --- |
| Repo/context reconfirmation | complete | Dirty worktree and OCR seams understood |
| Planning files | complete | `task_plan.md`, `findings.md`, `progress.md` created and updated |
| Real-data tooling | complete | Inventory and local workspace scripts with tests |
| OCR engine seam | complete | EasyOCR and Paddle adapters behind one interface |
| Benchmark extension | complete | `--engine easyocr|paddle`, matrix support, tests |
| Evidence checks | in_progress | Fixture, benchmark, matrix, repeatability, GUI, and EasyOCR package checks have evidence |
| Live workbook gate | blocked | Prepared copied workbook workspace; real GUI run artifacts are still missing |
| Paddle package gate | blocked | Existing EasyOCR package passes; Paddle-inclusive package is not yet validated |
| Docs/commit/push | pending | Docs updated, focused commits pushed |

## Guardrails

- Never write to the production network folder.
- Use `.analysis_tmp/real_data/...` for copied real data and generated artifacts.
- Do not commit workbooks, screenshots, OCR crops, raw OCR reports, `.analysis_tmp`,
  `settings.json`, `dist`, or `build`.
- Do not make PaddleOCR the default unless evidence gates pass.
- Keep both launchers working and keep GUI behavior unchanged.

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| Existing paused goal prevented `create_goal` | Tried to create a new goal | Continue under the existing thread goal; do not mark complete until evidence gates pass |
| `python-testing` skill not under `.codex/skills` | Read wrong path | Re-read from `C:\Users\leeho22\.agents\skills\python-testing\SKILL.md` |
| PowerShell `rg` glob `requirements*.txt` caused OS error 123 | Included wildcard as literal path in rg command | Use `rg --files` or explicit requirement files for future scans |
| First targeted pytest/ruff run timed out | Parallel verification after a long patch left stale Python processes | Killed stale pytest processes and reran targeted tests successfully |
| PaddleOCR full pipeline failed with a oneDNN PIR attribute error | First PaddleOCR 3.5 pipeline probe in the local validation venv | Use `TextRecognition` by default, `paddle_static`, `enable_mkldnn=False`, and CPU threads under the adapter |
| Source GUI smoke timed out when launched through `.venv\Scripts\python.exe` | Windows venv redirector put the Tk window on a child PID | Source smoke now follows child PIDs for source launchers |
| Full evidence bundle rejected live gates | Ran bundle with required live gates before an actual GUI workbook run | Keep Paddle optional/default-not-promoted until copied-workbook live smoke and live comparison artifacts exist |
