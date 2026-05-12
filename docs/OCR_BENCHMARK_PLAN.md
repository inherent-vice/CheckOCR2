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

Bootstrap a review-required fixture draft from saved detail images:

```powershell
python scripts\prepare_ocr_fixtures.py --source-dir .analysis_tmp\detail_images --output-dir tests\fixtures\ocr_crops
```

The script copies `*_date.png` and `*_rate.png` crops into the ignored fixture
folder and writes `ground_truth_draft.csv` rows with blank `expected_text`
values. Fill those values manually from the source screen, remove draft markers
from `notes`, then promote the reviewed draft:

```powershell
python scripts\promote_ocr_fixtures.py --draft-csv tests\fixtures\ocr_crops\ground_truth_draft.csv --reviewed-by <name> --confirm-reviewed
```

The promotion gate refuses blank or unnormalized expected values, remaining
draft markers, missing crops, duplicate paths, unsafe output placement, and
overwrite without `--overwrite`. If you intentionally want to prefill draft
values from a run report for review, add `--run-report <path>
--fill-expected-from-report`; those values still require manual verification
before baseline use. See
`docs/OCR_FIXTURE_WORKFLOW.md` for the end-to-end fixture workflow. The
preparer refuses to write `ground_truth.csv` directly and blocks output outside
the ignored fixture, analysis, or temp folders unless `--allow-unsafe-output`
is passed deliberately.

Once `ground_truth.csv` exists, omit `--allow-empty-fixture` so a missing or
empty fixture set fails the check.

Audit real fixtures before recording a baseline:

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp/ocr_fixture_audit.json
```

The audit fails until crop paths are readable, expected values are already
normalized, duplicate paths are removed, and the fixture set meets the minimum
date/rate counts. It also rejects blank `expected_text` cells and draft markers
such as `review_required` or `expected_from_run_report`. The default gate is
100 total crops with at least 50 date and 50 rate cases; pass smaller
`--min-*` values only for local dry runs.

Run the current baseline:

```powershell
python scripts/benchmark_ocr.py --output-json .analysis_tmp/easyocr_baseline.json
```

Compare preprocessing settings:

```powershell
python scripts/benchmark_ocr.py --upscale-factor 1.5 --upscale-method BICUBIC --output-json .analysis_tmp/easyocr_1_5_bicubic.json
python scripts/benchmark_ocr.py --detail 1 --output-json .analysis_tmp/easyocr_detail_1.json
python scripts/benchmark_ocr.py --allowlist-mode field --output-json .analysis_tmp/easyocr_field_allowlist.json
```

Run the preprocessing/detail matrix:

```powershell
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --output-json .analysis_tmp/ocr_benchmark_matrix.json
python scripts\benchmark_ocr_matrix.py --allowlist-modes none,field --output-json .analysis_tmp/ocr_benchmark_matrix_allowlist.json
```

The matrix runner sweeps upscale factors, interpolation methods, and EasyOCR
detail modes. Defaults are factors `1.0,1.5,2.0,2.5,3.0`, methods
`BILINEAR,BICUBIC,LANCZOS`, details `0,1`, and allowlist mode `none`.
Pass `--allowlist-modes none,field` to include field-specific EasyOCR
character allowlists for date and rate crops. It compares every candidate
against the first combination as the baseline, so use the default ordering to
keep `detail=0`, factor `1.0`, method `BILINEAR`, and allowlist `none` as the
reference. Matrix summaries include `field_comparisons` under each baseline
comparison; treat any date or rate field regression as a failed candidate even
when combined accuracy is unchanged.

Reports include raw OCR text and crop paths, so write them under
`.analysis_tmp/`. The script rejects other repository-local output paths unless
`--allow-repo-output` is supplied intentionally. Baseline reports also include
`field_summaries` for date and rate crops so one field's regression cannot be
hidden by another field's improvement. Use
`blank_on_expected_nonempty_count` as the blank-error metric; plain
`blank_count` also includes correctly blank expected-empty crops.

## Live Run Comparison

Before reducing fixed waits or changing OCR defaults, run the same 10 or more
rows twice and compare the generated run reports:

```powershell
python scripts\prepare_live_smoke_workspace.py --source-excel <workbook.xlsx> --output-dir .analysis_tmp\live_smoke --rows 2
```

For the 1-2 row GUI smoke, use the generated `live_smoke_input.xlsx` and
`.analysis_tmp\live_smoke` output folder so the original workbook is not the
run target. The manifest records source and smoke workbook hashes plus expected
`_updated.xlsx` and run-report paths.

```powershell
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --require-p95-improvement --min-p95-improvement-percent 10 --output-json .analysis_tmp/live_ocr_compare.json
```

The comparator checks that the input workbook path and row identities match,
date/rate outputs are unchanged, blank fields do not increase, failure rows do
not increase, timing values are parseable, and, when requested, P95 row-total
time improves by the configured percentage. Matrix comparisons also include
`coverage_unchanged`, so candidates with missing or invalid fixture coverage are
not treated as normal field comparisons. Use `--allow-output-changes` only for a
manual review run where changed OCR output is expected and will be checked
against source data.

## Evidence Bundle Gate

After the fixture audit, baseline benchmark, matrix benchmark, and live
comparison have all been produced, run the bundle gate:

```powershell
python scripts\check_ocr_evidence_bundle.py --audit-json .analysis_tmp\ocr_fixture_audit.json --benchmark-json .analysis_tmp\easyocr_baseline.json --matrix-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json --live-comparison-json .analysis_tmp\live_ocr_compare.json --require-live-comparison --output-json .analysis_tmp\ocr_evidence_bundle.json
```

This command is intentionally fail-closed. It rejects not-ready fixture audits,
dry-run or zero-case benchmarks, matrix candidates with changed coverage or
rejected live comparisons. Matrix accuracy, blank, false-positive, and P95
regressions are reported as warnings because exploratory matrices often contain
bad candidates by design. Add `--require-no-matrix-regressions` when the matrix
contains only selected promotion candidates. Omit `--require-live-comparison`
only when auditing fixture OCR accuracy without making wait-time or
runtime-default changes.

## Acceptance Gate

Adopt a candidate only when exact normalized date/rate accuracy does not
regress, fixture coverage is unchanged, `blank_on_expected_nonempty_count` does
not increase, false positives do not increase, and P95 latency improves or
packaging size materially drops across three consecutive fixture runs.
