# Reimplementation Completion Audit

Date: 2026-05-13

## Objective

Follow the shared CheckOCR2 modernization plan completely while preserving the
existing operator workflow. Completion means the code, package, GUI parity, OCR
evidence, and release gates are all backed by concrete artifacts, not only by
passing unit tests or partial smoke checks.

## Audit Result

Status: **not complete**.

The structural modernization and package gates are green. The copied-real-data
OCR fixture, benchmark, matrix, and repeatability evidence has progressed, and
PaddleOCR 3.5.0 with PaddlePaddle 3.3.1 is installed in `.venv`. The real
completion blockers are now the actual GUI copied-workbook live smoke,
same-input live comparison, and Paddle-inclusive package smoke. Do not mark the
plan complete and do not promote PaddleOCR as the default until those gates pass
with real data.

## 2026-05-13 Evidence Update

- Package-index checks show `paddleocr 3.5.0` is latest and `paddlepaddle 3.3.1`
  is latest for this Windows/Python 3.12 environment; `.venv` was upgraded and
  `paddle.utils.run_check()` passed on CPU.
- Paddle defaults now use `["ko", "en"]`, selecting
  `korean_PP-OCRv5_mobile_rec` for the Korean CouponCheck workflow while
  leaving EasyOCR at `["en"]`.
- Copied real data was prepared for `20260513`, `20260512`, and `20260511`.
  The local fixture audit has 349 cases: 177 date and 172 rate.
- Latest default Paddle fixture baseline:
  exact accuracy `0.9799426934097422`, date `0.9943502824858758`,
  rate `0.9651162790697675`, blank count `0`, false positive count `0`,
  p95 `188.42 ms`.
- Copied-real-data replay on 10 rows from `20260513` accepted EasyOCR vs
  default Paddle comparison: output changes `0`, blank increase `0`, failure
  increase `0`, p95 row time `1040.870 ms -> 266.721 ms` (`74.375%`
  improvement).
- This replay is explicitly marked `execution_mode=real_data_replay` and is
  not accepted as a substitute for the actual GUI live-smoke gate.
- `en_PP-OCRv5_mobile_rec` and `PP-OCRv5_server_rec` were rejected on the same
  replay because they introduced blank-rate regressions.

## Prompt-To-Artifact Checklist

| Requirement | Concrete artifact or command | Current evidence | Status |
| --- | --- | --- | --- |
| Preserve all supported launch paths | `python check_capture_ocr.py`; `python Check_Capture_Excel_V6.1_배포.py`; `python -m checkocr2.main` | Source GUI smokes recorded in `docs/GUI_PARITY_CHECKLIST.md`; all reached `Ready`, verified isolated settings, `1044x788` window, and clean exit. | Done |
| Keep root launcher compatible while package owns app shell | `check_capture_ocr.py`, `checkocr2/app.py`, `checkocr2/main.py`, `tests/test_logging_and_main.py` | `CheckCaptureOCRApp` lives in `checkocr2.app`; root import aliases the package app module; regression test pins both. | Done |
| Move legacy workflow manager out of root shell | `checkocr2/ocr_workflow_manager.py`, `tests/test_ocr_workflow_manager.py` | Manager class lives under `checkocr2`; export dialogs are injected from the app shell instead of importing Tk messagebox directly; focused and full tests passed after extraction. | Done |
| Keep GUI parity for menus, toolbar, shortcuts, file/grid flows, coordinates, options, presets, logs, and workflow summaries | `docs/GUI_PARITY_CHECKLIST.md` and listed focused pytest commands | Checklist records automated evidence for all listed areas except real live OCR run. Live-smoke workspace prepare/check guards exist, but they are not substitutes for the real 1-2 row run. | Partial |
| Keep runtime settings and logs out of repo root | `checkocr2/settings.py`, `checkocr2/logging_config.py`, `tests/test_logging_and_main.py` | Tests verify APPDATA settings/log placement and no repo-root `ocr_app.log` creation. | Done |
| Keep worker, stop-state, Excel blank, date validation, and exception safety fixes | `tests/test_worker.py`, `tests/test_work_controller.py`, `tests/test_excel_table_modules.py`, `tests/test_ocr_field_analysis.py` | Full suite currently includes these regressions and passes. | Done |
| Keep package release gate green | Clean PyInstaller build plus `scripts/package_smoke.py ... --ocr-ready-mode real ... --require-clean-exit` | Strict package smoke: `596.409 MB`, startup `1.125s`, build date `2026-05-12T10:50:04+00:00`, `Ready`, isolated settings, clean exit. | Done |
| Build reviewed OCR crop fixtures | `.analysis_tmp/ocr_crops/ground_truth.csv`; `python scripts/audit_ocr_fixtures.py --output-json .analysis_tmp/ocr_fixture_audit.json` | Local copied-real-data fixture audit is accepted with 349 cases. The committed `tests/fixtures/ocr_crops/ground_truth.csv` remains absent by design because real crops/raw text are not committed. | Partial |
| Record real EasyOCR baseline on audited fixtures | `python scripts/benchmark_ocr.py --engine easyocr --fixture-csv .analysis_tmp/ocr_crops/ground_truth.csv --output-json .analysis_tmp/easyocr_baseline.json` | Accepted local EasyOCR baseline exists: 349 cases, exact accuracy `0.9426934097421203`. | Done |
| Run OCR matrix on audited fixtures | `python scripts/benchmark_ocr_matrix.py --engines easyocr,paddle --output-json .analysis_tmp/ocr_engine_matrix.json` | Non-dry-run local matrix exists. Strict promotion still depends on live-smoke/live-comparison artifacts. | Partial |
| Prove candidate repeatability across three fixture runs | `python scripts/check_ocr_repeatability.py --benchmark-json .analysis_tmp\paddle_korean_repeat_1.json .analysis_tmp\paddle_korean_repeat_2.json .analysis_tmp\paddle_korean_repeat_3.json --output-json .analysis_tmp\paddle_korean_repeatability.json` | Accepted for the exact default Paddle model, p95 latency min/mean/max `153.22 / 211.85 / 273.34 ms`. | Done |
| Run copied-workbook live smoke before speed/default changes | `python scripts/prepare_live_smoke_workspace.py ...`; `python scripts/check_live_smoke_workspace.py ...` | Prepare/check guards exist, but no accepted real live-smoke check artifact is present. | Missing |
| Run same-input live comparison before speed/default changes | `python scripts/compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json ...` | No accepted live comparison artifact is present. | Missing |
| Pass final OCR evidence bundle | `python scripts/check_ocr_evidence_bundle.py ... --require-repeatability --require-live-smoke --require-live-comparison ...` | Current final bundle is still rejected because actual GUI live smoke and same-input live comparison are missing. | Missing |

## Current Verifier Snapshot

Current local evidence artifacts:

- `.analysis_tmp/ocr_fixture_audit.json`: accepted, 349 cases, 177 date,
  172 rate.
- `.analysis_tmp/easyocr_baseline.json`: accepted local EasyOCR baseline,
  exact accuracy `0.9426934097421203`.
- `.analysis_tmp/paddle_korean_baseline.json`: accepted latest default Paddle
  fixture baseline, exact accuracy `0.9799426934097422`, blank count `0`,
  false positive count `0`, p95 `188.42 ms`.
- `.analysis_tmp/real_data_replay/easyocr_vs_paddle_default_latest_replay_compare.json`:
  accepted copied-real-data replay comparison, output changes `0`, p95 row
  time `1040.870 ms -> 266.721 ms`.
- `.analysis_tmp/paddle_korean_repeatability.json`: accepted latest default
  Paddle repeatability for three runs.
- `.analysis_tmp/ocr_engine_matrix_paddle_promotion.json`: selected
  EasyOCR-vs-default-Paddle matrix; accuracy, blank, false-positive, and
  coverage gates pass, while crop-level p95 is warning-only because live replay
  p95 passes.
- `.analysis_tmp/ocr_evidence_bundle_paddle_promotion_current.json`: final
  bundle still `accepted=false`; fixture, benchmark, selected matrix,
  repeatability, and replay comparison checks pass, but live smoke is rejected
  because the actual GUI output workbook/report are missing.
- `.analysis_tmp/live_smoke_check.json` and `.analysis_tmp/ocr_evidence_bundle.json`:
  still not ready because the actual GUI live-smoke workbook/report is missing
  and the promotion bundle now treats matrix regressions as hard failures. A
  selected-candidate matrix/report must be used for final promotion.

## Next Required Work

1. Run the actual GUI workflow against the prepared copied workbook in
   `.analysis_tmp\live_smoke`, never the production network workbook.
2. Verify the produced workbook/report with
   `scripts\check_live_smoke_workspace.py`.
3. Preserve same-input EasyOCR and default Paddle live run reports, then pass
   `scripts\compare_run_reports.py`.
4. Re-run repeatability and selected-candidate matrix if OCR settings,
   preprocessing, or model choices change.
5. Build a Paddle-inclusive package and pass package smoke with acceptable
   startup, size, metadata, and model-cache behavior.
6. Run
   `scripts\check_ocr_evidence_bundle.py --require-repeatability --require-live-smoke --require-live-comparison`;
   only then consider OCR default, wait-time, confidence, preprocessing, or
   engine promotion.
