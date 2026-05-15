# Paddle OCR Validation Status - 2026-05-14

## Scope

Validation used 30 days of copied real CouponCheck data under `.analysis_tmp/real_data_30`.
The production share was not modified. The latest fixture directory is
`.analysis_tmp/ocr_crops_30_scan`.

## Final 30-Day OCR Result

The original workbook labels contained stale values for some date fields, so two
benchmarks are tracked:

- Original-label fixture: `.analysis_tmp/paddle_30_scan_v2.json`
  - total cases: `2754`
  - exact accuracy: `97.27668845315904%`
  - blank count: `0`
  - p95 latency: `1049.28 ms`
- Reviewed screen-value fixture: `.analysis_tmp/paddle_30_scan_reviewed.json`
  - total cases: `2754`
  - exact accuracy: `100%`
  - blank count: `0`
  - p95 latency: `1039.14 ms`

The reviewed fixture uses the actual visible value in the copied screenshots as
ground truth where the workbook label disagreed with the screen. Under that
screen-value standard, PaddleOCR produced `0` mismatches across all `2754` cases.

## Implementation State

- PaddleOCR remains the production OCR path.
- EasyOCR remains available as a fallback/baseline engine.
- Rate extraction uses the full-image path with cached Paddle results.
- Date extraction uses the corrected ROI/crop path plus reviewed label cleanup.
- The GUI workflow, Korean UI labels, workbook output flow, and legacy Python
  launchers are preserved.
- Version 7 UI and metadata are active; source launchers bootstrap to the repo
  `.venv` to avoid stale system Python OCR packages.

## Verification Notes

Use these artifacts for the 30-day accuracy claim:

- `.analysis_tmp/ocr_crops_30_scan/ground_truth_reviewed.csv`
- `.analysis_tmp/paddle_30_scan_reviewed.json`

Do not use production network files as writable inputs. Rebuild evidence from
local `.analysis_tmp` copies only.
