# Startup Loading Optimization Progress

## 2026-05-15

- Read `docs/STARTUP_LOADING_OPTIMIZATION_PLAN_KO.md`.
- Confirmed current repo status only had existing untracked `.claude/`.
- Confirmed implementation target: Phase 0-3 plus verification. `paddle-only` remains approval-gated.
- Created file-based planning artifacts per `planning-with-files` workflow.
- Added startup trace JSONL events and source/package startup measurement script.
- Added OCR loading overlay for `RuntimeState.OCR_LOADING`.
- Converted Paddle blank fallback to lazy EasyOCR loading and exposed loaded/init metrics in package smoke status.
- Added Paddle cache warm script and optional build-time model inclusion through `CHECKOCR2_PACKAGE_PADDLE_MODELS`.
- Updated rate-normalization tests and fixture audit alias handling for the V7 default 4 decimal places.
- Verification so far: `ruff`, `compileall`, and full `pytest` passed.
- Source GUI smoke passed for both `check_capture_ocr.py` and `Check_Capture_Excel_V6.1_배포.py` with real Paddle OCR ready.
- Built `dist/CheckCaptureOCR_V7.0/CheckCaptureOCR_V7.0.exe` as a Paddle package with `korean_PP-OCRv5_mobile_rec` bundled.
- Package smoke passed with package size `1066.554 MB`, real Paddle OCR ready, and `ocr_fallback_loaded=false`.
- Startup measurement passed: source 3 runs `2.719-3.047s`; package 3 runs `1.562-2.078s`.
