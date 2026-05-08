# OCR Benchmark Plan

This repository now has a benchmark harness at `scripts/benchmark_ocr.py`.
It is intentionally evidence-first: do not change OCR engines, confidence
thresholds, or fixed delays until a repeatable fixture run shows the tradeoff.

## Fixture Format

Create `tests/fixtures/ocr_crops/ground_truth.csv` with these columns:

```csv
crop_path,field,expected_text,source_run,notes
sample_date_001.png,date,2026/05/08,manual,
sample_rate_001.png,rate,3.500,manual,
```

`crop_path` must be relative to the CSV folder. `tests/fixtures/ocr_crops/` is
ignored because real crops can contain production screen data; commit only
sanitized fixtures in a reviewed follow-up if they are safe to publish.

## Commands

Validate the harness without OCR:

```powershell
python scripts/benchmark_ocr.py --dry-run --allow-empty-fixture
```

Once `ground_truth.csv` exists, omit `--allow-empty-fixture` so a missing or
empty fixture set fails the check.

Run the current baseline:

```powershell
python scripts/benchmark_ocr.py --output-json .analysis_tmp/easyocr_baseline.json
```

Compare preprocessing settings:

```powershell
python scripts/benchmark_ocr.py --upscale-factor 1.5 --upscale-method BICUBIC --output-json .analysis_tmp/easyocr_1_5_bicubic.json
python scripts/benchmark_ocr.py --detail 1 --output-json .analysis_tmp/easyocr_detail_1.json
```

Reports include raw OCR text and crop paths, so write them under
`.analysis_tmp/`. The script rejects other repository-local output paths unless
`--allow-repo-output` is supplied intentionally.

## Acceptance Gate

Adopt a candidate only when exact normalized date/rate accuracy does not
regress, blank fields do not increase, false positives do not increase, and P95
latency improves or packaging size materially drops across three consecutive
fixture runs.
