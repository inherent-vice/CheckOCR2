# OCR Fixture Workflow

This workflow turns saved date/rate detail screenshots into audited OCR ground
truth. Use it before changing OCR defaults, preprocessing, confidence
thresholds, fixed waits, or OCR engines.

## 1. Save Source Crops

Save representative detail images outside tracked source, for example under
`.analysis_tmp\detail_images`. The preparer only picks files ending in
`*_date.png` and `*_rate.png`.

Keep real screenshots local. `tests/fixtures/ocr_crops/` and `.analysis_tmp/`
are ignored because crops, coordinates, workbook names, and OCR text can expose
production data.

## 2. Prepare A Draft

```powershell
python scripts\prepare_ocr_fixtures.py --source-dir .analysis_tmp\detail_images --output-dir tests\fixtures\ocr_crops
```

The script copies crops into `tests\fixtures\ocr_crops\` and writes
`ground_truth_draft.csv`. Draft rows are intentionally not trusted: blank
`expected_text` values and `review_required` notes make the audit fail. The
preparer refuses to write `ground_truth.csv` directly; promotion must be a
separate manual-review step.

To prefill draft text from a run report for review only:

```powershell
python scripts\prepare_ocr_fixtures.py --source-dir .analysis_tmp\detail_images --run-report .analysis_tmp\run_report.json --fill-expected-from-report
```

Prefilled values still get an `expected_from_run_report` marker, so they cannot
pass the audit until manually checked.

By default, output is limited to the ignored fixture folder, `.analysis_tmp\`,
or the system temp folder. Use `--allow-unsafe-output` only for deliberate local
experiments.

## 3. Review And Promote

Open `ground_truth_draft.csv`, compare every crop against the source screen or
authoritative data, and fill normalized `expected_text` values:

- Dates: `YYYY/MM/DD`, for example `2026/05/11`.
- Rates: three decimals, for example `3.500`.

Remove draft markers from `notes`, then run the promotion gate:

```powershell
python scripts\promote_ocr_fixtures.py --draft-csv tests\fixtures\ocr_crops\ground_truth_draft.csv --reviewed-by <name> --confirm-reviewed
```

The promotion script writes `ground_truth.csv` only after explicit review
confirmation, nonblank normalized expected values, no draft markers, readable
crop files, duplicate checks, and the same fixture audit gate all pass. It
refuses overwrite unless `--overwrite` is supplied and supports `--dry-run` for
checking a reviewed draft without writing the canonical CSV.

## 4. Audit The Ground Truth

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json
```

The audit must report `ready`. It rejects missing or unreadable images, duplicate
crop paths, unsupported fields, blank expected values, unnormalized text, draft
markers, and insufficient coverage. The default coverage gate is 100 total
crops with at least 50 date and 50 rate cases. Promotion already runs this
audit once; rerun it here to produce the baseline evidence JSON.

## 5. Benchmark And Compare Live Runs

```powershell
python scripts\benchmark_ocr.py --output-json .analysis_tmp\easyocr_baseline.json
python scripts\benchmark_ocr_matrix.py --allowlist-modes none,field --output-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --require-p95-improvement --min-p95-improvement-percent 10 --output-json .analysis_tmp\live_ocr_compare.json
python scripts\check_ocr_evidence_bundle.py --audit-json .analysis_tmp\ocr_fixture_audit.json --benchmark-json .analysis_tmp\easyocr_baseline.json --matrix-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json --live-comparison-json .analysis_tmp\live_ocr_compare.json --require-live-comparison --output-json .analysis_tmp\ocr_evidence_bundle.json
```

Adopt a candidate only when audited fixture accuracy does not regress, blank and
failure counts do not increase, and same-input live P95 timing improves when a
speed claim is being made. The evidence bundle gate is the final guard against
mistaking dry-run, zero-case, not-ready, coverage-changed, or rejected live
comparison artifacts for usable OCR evidence; use
`--require-no-matrix-regressions` for strict selected-candidate bundles.
