# Findings: CheckOCR2 PaddleOCR Production Readiness

## Current Repo State

- `master` is aligned with `origin/master`.
- Only unrelated untracked file observed at start: `.claude/settings.local.json`.
- Existing OCR code is still EasyOCR-oriented:
  - `checkocr2/ocr_engine.py`
  - `checkocr2/ocr_reader_lifecycle.py`
  - `checkocr2/ocr_workflow_manager.py`
  - `scripts/benchmark_ocr.py`
  - `scripts/benchmark_ocr_matrix.py`
- Tests install an EasyOCR stub in `tests/conftest.py`, so Paddle support should
  be tested with import stubs and without loading real models.

## Official PaddleOCR Check

- PyPI reports `paddleocr` 3.5.0 uploaded on 2026-04-21.
- GitHub `PaddlePaddle/PaddleOCR` latest release is v3.5.0, dated 2026-04-21.
- PaddleOCR 3.x documentation describes PP-OCRv5 as the default OCR pipeline and
  documents non-compatible API changes from 2.x.

## Real CouponCheck Data

- Production data path is readable:
  `\\10.10.10.11\파생상품평가본부\B.SWAP평가팀\8_엑셀수동일일평가\CouponCheck\CHECK`.
- Observed pattern:
  - root workbook: `List_CouponCheck_(YYYYMMDD).xlsx`
  - root result workbook: `List_CouponCheck_(YYYYMMDD)_updated.xlsx`
  - day folder: `List_CouponCheck_(YYYYMMDD)\종목코드.png`
- Recent sample counts:
  - 2026-05-13: 69 PNG files
  - 2026-05-12: 79 PNG files
  - 2026-05-11: 110 PNG files
- Recent sample image sizes vary: 884x496, 747x428, 691x425.
- Recent day folders did not contain `*_date.png` or `*_rate.png` files.

## Real-Data Tooling Verification

- `scripts/inventory_couponcheck_real_data.py` wrote
  `.analysis_tmp/real_data_inventory.json` successfully from the real network
  path.
- Real inventory result, limited to the latest 5 day folders:
  - total day folders discovered: 141
  - inventoried day count: 5
  - PNG total: 388
  - date/rate crop total: 0/0
  - sampled image sizes: 884x496, 747x428, 748x417, 715x406, 691x425
- `scripts/prepare_real_data_workspace.py` copied latest day `20260513` into
  `.analysis_tmp/real_data`.
- Real workspace manifest summary:
  - copied file count: 71
  - PNG count: 69
  - workbook/result workbook/image hashes matched source hashes

## Implementation Implications

- Real-data tooling should inventory workbook/result/image availability before
  OCR changes.
- Historical full-area PNGs are not enough for current benchmark fixture format
  without either live crop regeneration or a separate crop extraction tool.
- The engine interface should keep EasyOCR behavior byte-compatible enough for
  existing tests and GUI readiness paths.

## PaddleOCR Validation Results

- PaddleOCR 3.5.0 required an isolated `.venv`; the system Python still contains
  older `paddleocr==2.9.1` and a broken Paddle/protobuf combination.
- Full `PaddleOCR` pipeline mode hit a Windows CPU oneDNN/PIR runtime error.
  The working adapter default is `TextRecognition` with `paddle_static`,
  `enable_mkldnn=False`, and `en_PP-OCRv5_mobile_rec`.
- Real-data fixture audit passed on 349 cases from copied `20260513`,
  `20260512`, and `20260511` data.
- Current GUI-equivalent benchmark setting is `2.0x LANCZOS`, `detail=0`, and
  no allowlist.
- EasyOCR repeatability: accepted, exact accuracy `0.9426934097421203`, p95
  mean `144.710 ms`.
- Paddle repeatability: accepted, exact accuracy `0.9828080229226361`, p95 mean
  `138.787 ms`.
- Paddle improves date accuracy from `0.9943502824858758` to `1.0` and rate
  accuracy from `0.8895348837209303` to `0.9651162790697675` on the real-data
  crop set.
- Paddle real source GUI readiness passed for all three launch paths in the
  `.venv` validation environment.
- The existing EasyOCR package still builds and passes strict package smoke:
  package size `596.417 MB`, startup `4.265 s`, window `1216x889`, clean exit.

## Remaining Gates

- Paddle is not promoted as default in `DEFAULT_SETTINGS`; `easyocr` remains the
  repository default until the required live and Paddle-package gates pass.
- `.analysis_tmp/live_smoke/live_smoke_input.xlsx` is prepared from copied
  `20260513` data, but no real GUI workbook run has produced
  `live_smoke_input_updated.xlsx` or `live_smoke_input_run_report.json`.
- Full evidence bundle with required live gates is `not_ready` because live
  smoke and live comparison artifacts are missing.
- Paddle-inclusive PyInstaller packaging is not validated. The existing package
  policy and build spec are still EasyOCR/OpenCV-headless oriented.
