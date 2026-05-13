# Paddle OCR Validation Status - 2026-05-13

## Scope

This status records the PaddleOCR 3.5.0 / PP-OCRv5 validation work for
CheckOCR2. Production network data was read only; all workbooks, screenshots,
crops, reports, and model caches were copied or generated under
`.analysis_tmp/`.

Package-index verification on 2026-05-13 confirms `paddleocr==3.5.0` as the
latest PaddleOCR release and `paddlepaddle==3.3.1` as the latest applicable
Windows CPU runtime for this Python 3.12 environment. The repo `.venv` has both
versions installed and `paddle.utils.run_check()` passed on CPU.

## Implemented

- Added copied-real-data inventory and workspace tooling:
  `scripts/inventory_couponcheck_real_data.py` and
  `scripts/prepare_real_data_workspace.py`.
- Added full-area screenshot crop extraction:
  `scripts/extract_real_data_ocr_fixtures.py`.
- Added an OCR engine seam in `checkocr2/ocr_engine.py` and a PaddleOCR
  adapter in `checkocr2/ocr_paddle_engine.py`.
- Set Paddle defaults to `["ko", "en"]`, selecting
  `korean_PP-OCRv5_mobile_rec` for this Korean CouponCheck workflow. EasyOCR
  remains available as the baseline and fallback engine.
- Extended benchmark/matrix scripts with `--engine easyocr|paddle` and
  `--engines easyocr,paddle`.
- Added `CHECKOCR2_OCR_ENGINE` for smoke/local validation without changing user
  settings files.
- Added a production Paddle blank fallback: when Paddle returns no OCR text for
  a crop, the app retries that crop with EasyOCR English CPU. Fallback usage is
  now written to run reports and package-smoke status so Paddle evidence cannot
  silently include fallback output.
- Promoted Paddle as the repository default in `DEFAULT_SETTINGS` after the
  promotion evidence bundle passed.
- Added a Paddle PyInstaller profile with bundled Paddle native DLLs, OCR-core
  metadata, runtime DLL-path hook, and package-smoke checks that reject false
  Paddle readiness when the app actually falls back to EasyOCR.

## Evidence

- Real data copied: `20260513`, `20260512`, `20260511`.
- Fixture audit: `.analysis_tmp/ocr_fixture_audit.json` accepted, 349 cases
  total, 177 date and 172 rate.
- EasyOCR fixture baseline: `.analysis_tmp/easyocr_baseline.json` accepted,
  exact accuracy `0.9426934097421203`, p95 latency `107.86 ms`.
- Default Paddle fixture baseline:
  `.analysis_tmp/paddle_korean_baseline.json` accepted, exact accuracy
  `0.9799426934097422`, date accuracy `0.9943502824858758`, rate accuracy
  `0.9651162790697675`, blank count `0`, false positive count `0`, p95 latency
  `188.42 ms`.
- Default Paddle repeatability:
  `.analysis_tmp/paddle_korean_repeatability.json` accepted for three runs,
  p95 latency min/mean/max `153.22 / 211.85 / 273.34 ms`.
- Selected promotion matrix:
  `.analysis_tmp/ocr_engine_matrix_paddle_promotion.json` accepted for EasyOCR
  vs default Paddle. Accuracy, blank, false-positive, and coverage gates pass.
  Crop-level p95 is slower and remains a warning because same-input live row
  p95 improves.
- Copied-workbook local GUI simulator smoke:
  `.analysis_tmp/live_smoke_check_paddle.json` accepted on 10 copied real rows
  from `20260513`.
- Same-input live comparison:
  `.analysis_tmp/live_ocr_compare.json` accepted, output changes `0`, blank
  increase `0`, failure increase `0`, p95 row time
  `2374.435 ms -> 1902.458 ms` (`19.877%` improvement).
- Paddle live run report:
  `.analysis_tmp/paddle_live_run_report.json` processed 10 rows, status
  `완료=10`, blank date `1`, blank rate `1`, and `ocr_fallback_count=0`.
- Final promotion evidence bundle:
  `.analysis_tmp/ocr_evidence_bundle_paddle_promotion_final.json` accepted with
  fixture audit, Paddle benchmark, selected matrix, repeatability, live smoke,
  and live comparison all green. The only warnings are the crop-level p95
  matrix warnings.
- Source GUI smoke passed for both supported launchers with isolated settings,
  minimum `1000x600` window size, ready state, and clean exit.
- Paddle-inclusive PyInstaller build passed with
  `CHECKOCR2_PACKAGE_PADDLE=1`.
- Paddle-inclusive package smoke:
  `.analysis_tmp/paddle_package_smoke_real.json` accepted with
  `ocr_ready_mode=real`, `package_profile=paddle`, `paddleocr 3.5.0`,
  `paddlepaddle 3.3.1`, actual engine `paddle`, fallback enabled to `easyocr`,
  fallback count `0`, package size `996.392 MB`, startup/window elapsed
  `1.156 s`, window `1216x889`, isolated settings file, no packaged
  `opencv-python`, and clean GUI exit.

## Decision

PaddleOCR 3.5.0 with PP-OCRv5 is the accepted default OCR path for CheckOCR2.
For this Korean CouponCheck workflow, `korean_PP-OCRv5_mobile_rec` is the best
validated Paddle candidate. EasyOCR remains available as an explicit baseline
engine and as a recorded blank fallback.

The Paddle-inclusive OneDIR package is large (`996.392 MB`) but passes the
current package readiness gate. Package-size/model-cache optimization is a
follow-up deployment task, not a blocker for this validation slice.

## Follow-Ups

- Re-run selected-candidate matrix/repeatability if OCR settings, model cache,
  preprocessing defaults, or fallback behavior change.
- Re-run copied-workbook live comparison before changing OCR defaults,
  confidence rules, wait timing, or output workbook semantics.
- Treat package-size/model-cache optimization as a separate release hardening
  task.
