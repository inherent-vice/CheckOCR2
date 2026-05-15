# Startup Loading Optimization Task Plan

Goal: implement `docs/STARTUP_LOADING_OPTIMIZATION_PLAN_KO.md` for CheckOCR2 V7 without changing the current GUI workflow, OCR output contract, or workbook behavior.

## Phases

| Phase | Status | Scope |
| --- | --- | --- |
| Phase 0 | completed | Add startup tracing, persisted JSONL evidence, and startup measurement support. |
| Phase 1 | completed | Add OCR loading overlay tied to runtime state. |
| Phase 2 | completed | Convert EasyOCR blank fallback from eager initialization to lazy-load. |
| Phase 3 | completed | Add Paddle cache warm command/script and model-cache diagnostics. |
| Verification | completed | Run lint, compile, pytest, source GUI smoke, package build, package smoke, and startup measurement. |

## Success Criteria

- `checkocr2/startup_trace.py` records startup milestones under `%APPDATA%\CheckOCR2\logs\startup_trace.jsonl`.
- `scripts/measure_startup.py` reports source/package startup timing from real launches.
- Loading overlay appears while OCR is preparing and disappears on Ready.
- Paddle remains default; EasyOCR remains available but is loaded only when a blank Paddle result requires fallback.
- `scripts/warm_paddle_cache.py` can pre-create Paddle model cache.
- Source and package smoke pass with Paddle real OCR ready.

## Decisions

- Do not remove EasyOCR from the default package in this implementation. The plan marks `paddle-only` as approval-gated.
- Keep all network production folders untouched.
