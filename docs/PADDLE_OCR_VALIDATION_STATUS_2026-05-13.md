# Paddle OCR Validation Status - 2026-05-13

## Scope

This status records the current PaddleOCR 3.5.0 / PP-OCRv5 validation work for
CheckOCR2. Production network data was read only; all workbooks, screenshots,
crops, reports, and model caches were copied or generated under `.analysis_tmp/`.

Current package-index verification confirms `paddleocr==3.5.0` is the latest
available PaddleOCR release and `paddlepaddle==3.3.1` is the latest available
Windows CPU runtime for this Python 3.12 environment. The repo `.venv` was
updated to `paddleocr 3.5.0` plus `paddlepaddle 3.3.1`, and
`paddle.utils.run_check()` passed on CPU.

## Implemented

- Added copied-real-data inventory and workspace tools:
  `scripts/inventory_couponcheck_real_data.py` and
  `scripts/prepare_real_data_workspace.py`.
- Added full-area screenshot crop extraction:
  `scripts/extract_real_data_ocr_fixtures.py`.
- Added an OCR engine seam in `checkocr2/ocr_engine.py`.
- Added `checkocr2/ocr_paddle_engine.py` with a PaddleOCR 3.5
  `TextRecognition` adapter using PP-OCRv5 recognition.
- Set Paddle validation paths to use `["ko", "en"]` by default so
  `korean_PP-OCRv5_mobile_rec` is selected for this Korean CouponCheck
  workflow. EasyOCR remains `["en"]`.
- Extended benchmark tools with `--engine easyocr|paddle` and
  `--engines easyocr,paddle`.
- Added `CHECKOCR2_OCR_ENGINE` for smoke/local validation without changing user
  settings files.
- Updated source smoke PID matching so Windows venv redirector child processes
  are handled.

## Evidence

- Real data copied: `20260513`, `20260512`, `20260511`.
- Fixture audit: accepted, 349 cases total, 177 date and 172 rate.
- EasyOCR repeatability: accepted, exact accuracy `0.9426934097421203`, p95 mean
  `144.710 ms`.
- Earlier Paddle repeatability: accepted, exact accuracy `0.9828080229226361`,
  p95 mean `138.787 ms`.
- Earlier Paddle date accuracy: `1.0`; Paddle rate accuracy:
  `0.9651162790697675`.
- Paddle real source GUI smoke: passed for `check_capture_ocr.py`,
  `Check_Capture_Excel_V6.1_배포.py`, and `python -m checkocr2.main`.
- Existing EasyOCR package smoke: passed after rebuild, `596.417 MB`, startup
  `4.265 s`, window `1216x889`, clean exit.
- Latest Paddle runtime check: `.venv` has `paddleocr 3.5.0`,
  `paddlepaddle 3.3.1`; `paddle.utils.run_check()` passed on CPU.
- Copied real-data replay, 10 rows from `20260513`, EasyOCR baseline vs default
  Paddle (`korean_PP-OCRv5_mobile_rec`): accepted, output changes `0`, blank
  increase `0`, failure increase `0`, p95 row time `1040.870 ms -> 266.721 ms`
  (`74.375%` improvement).
- Rejected Paddle candidates on the same replay:
  `en_PP-OCRv5_mobile_rec` was fast but produced three extra blank rate fields;
  `PP-OCRv5_server_rec` produced two extra blank rate fields and was slower.
- Latest default Paddle fixture baseline on 349 copied-real-data crops:
  exact accuracy `0.9799426934097422`, date accuracy
  `0.9943502824858758`, rate accuracy `0.9651162790697675`, blank count `0`,
  false positive count `0`, p95 latency `188.42 ms`.
- Latest default Paddle repeatability:
  `.analysis_tmp/paddle_korean_repeatability.json` accepted for three runs,
  p95 latency min/mean/max `153.22 / 211.85 / 273.34 ms`.
- Selected promotion matrix:
  `.analysis_tmp/ocr_engine_matrix_paddle_promotion.json` compares EasyOCR vs
  default Paddle only. Accuracy, blank, false-positive, and coverage gates pass;
  crop-level p95 is slower and recorded as a warning because same-input
  copied-workbook replay proves live row p95 improvement.

## Decision

PaddleOCR is implemented and `korean_PP-OCRv5_mobile_rec` is the best current
Paddle candidate for this Korean CouponCheck workflow. It is not promoted as
the repository default yet. `easyocr` remains the default in `DEFAULT_SETTINGS`
until actual GUI live workbook comparison and Paddle-inclusive packaging pass.

## Open Gates

- Run the prepared copied workbook smoke in the actual GUI workflow and produce:
  `.analysis_tmp/live_smoke/live_smoke_input_updated.xlsx` and
  `.analysis_tmp/live_smoke/live_smoke_input_run_report.json`.
- Run same-input EasyOCR vs Paddle live comparison and produce
  `.analysis_tmp/live_ocr_compare.json`.
- Build a Paddle-inclusive EXE and pass package smoke with acceptable startup,
  size, metadata, and model-cache behavior.
- Re-run the selected-candidate promotion matrix/repeatability if OCR settings,
  model cache, or preprocessing defaults change.
- Re-run `scripts/check_ocr_evidence_bundle.py` with live smoke and live
  comparison required; it must return `accepted=true` before default promotion.
