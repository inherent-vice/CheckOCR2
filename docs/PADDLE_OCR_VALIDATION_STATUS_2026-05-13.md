# Paddle OCR Validation Status - 2026-05-13

## Scope

This status records the current PaddleOCR 3.5.0 / PP-OCRv5 validation work for
CheckOCR2. Production network data was read only; all workbooks, screenshots,
crops, reports, and model caches were copied or generated under `.analysis_tmp/`.

## Implemented

- Added copied-real-data inventory and workspace tools:
  `scripts/inventory_couponcheck_real_data.py` and
  `scripts/prepare_real_data_workspace.py`.
- Added full-area screenshot crop extraction:
  `scripts/extract_real_data_ocr_fixtures.py`.
- Added an OCR engine seam in `checkocr2/ocr_engine.py`.
- Added `checkocr2/ocr_paddle_engine.py` with a PaddleOCR 3.5
  `TextRecognition` adapter using PP-OCRv5 mobile recognition.
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
- Paddle repeatability: accepted, exact accuracy `0.9828080229226361`, p95 mean
  `138.787 ms`.
- Paddle date accuracy: `1.0`; Paddle rate accuracy:
  `0.9651162790697675`.
- Paddle real source GUI smoke: passed for `check_capture_ocr.py`,
  `Check_Capture_Excel_V6.1_배포.py`, and `python -m checkocr2.main`.
- Existing EasyOCR package smoke: passed after rebuild, `596.417 MB`, startup
  `4.265 s`, window `1216x889`, clean exit.

## Decision

PaddleOCR is implemented and validated as the leading OCR candidate, but it is
not promoted as the repository default yet. `easyocr` remains the default in
`DEFAULT_SETTINGS` until live workbook comparison and Paddle-inclusive packaging
pass.

## Open Gates

- Run the prepared copied workbook smoke in the actual GUI workflow and produce:
  `.analysis_tmp/live_smoke/live_smoke_input_updated.xlsx` and
  `.analysis_tmp/live_smoke/live_smoke_input_run_report.json`.
- Run same-input EasyOCR vs Paddle live comparison and produce
  `.analysis_tmp/live_ocr_compare.json`.
- Build a Paddle-inclusive EXE and pass package smoke with acceptable startup,
  size, metadata, and model-cache behavior.
- Re-run `scripts/check_ocr_evidence_bundle.py` with live smoke and live
  comparison required; it must return `accepted=true` before default promotion.
