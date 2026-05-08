# CheckOCR2

CheckOCR2 is a Windows desktop OCR automation tool for loading Excel rows,
copying stock codes into an external screen, capturing configured date/rate
regions, running EasyOCR, and exporting an updated workbook.

The current migration keeps the existing Tkinter GUI and operator workflow while
moving reusable logic into the `checkocr2/` package.

## Entry Points

- `python check_capture_ocr.py`: canonical development launcher.
- `python Check_Capture_Excel_V6.1_배포.py`: compatibility launcher for existing
  shortcuts and release habits.
- `python -m checkocr2.main`: package bootstrap path.
- `dist/CheckCaptureOCR_V6.1/CheckCaptureOCR_V6.1.exe`: PyInstaller OneDIR
  packaged executable after a build.

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python check_capture_ocr.py
```

For narrower installs:

- `requirements-runtime.txt`: runtime dependencies only.
- `requirements-build.txt`: runtime plus PyInstaller.
- `requirements-dev.txt`: build dependencies plus pytest and ruff.
- `constraints.txt`: pinned direct dependency versions from the verified Windows
  environment.

Runtime settings are stored outside the repo at
`%APPDATA%\CheckOCR2\settings.json`. Keep `settings.example.json` as the
source-controlled template only.

## Verification Commands

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture
python -m PyInstaller build_app.spec --noconfirm
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready
```

Run GUI smoke checks through all three Python entry points after touching
startup, settings, threading, or Tkinter UI state.

## Repository Map

- `check_capture_ocr.py`: current GUI shell and compatibility surface.
- `checkocr2/`: extracted package modules for settings, models, paths, OCR
  engine access, screen automation, workflow, worker helpers, reports, and
  runtime UI state, plus low-risk Tk panel builders.
- `tests/`: pytest characterization and unit tests with fakes for OCR, screen
  automation, and Tk-facing behavior.
- `scripts/`: OCR benchmark, benchmark-matrix, and packaged-EXE smoke tools.
- `docs/`: architecture, reimplementation, GUI parity, run report, and benchmark
  documentation.
- `legacy/`: historical versions kept for reference only.
- `tools/`: icon generation utilities.

## Generated Outputs

An OCR run writes `<input_stem>_updated.xlsx` and
`<input_stem>_run_report.json` in the selected output folder. The JSON report
contains per-row timing, status counts, blank-field counts, export timing, and
errors. Use it before changing OCR settings or fixed wait times.

Packaged builds include `checkocr2/build_metadata.json` with the app version,
build date, Python version, direct dependency versions, and dependency hash.
The package smoke script reports startup elapsed time, package size, and this
metadata when present. With `--require-ocr-ready`, it runs an explicit smoke
mode that bypasses real model loading and verifies the GUI reaches `Ready`.

Use `scripts\benchmark_ocr_matrix.py` after fixture creation to sweep OCR
upscale factors, interpolation methods, and EasyOCR detail modes against the
same ground-truth set. The matrix report compares every candidate with the
first combination as the baseline. Add `--allowlist-modes none,field` when
testing field-specific EasyOCR character allowlists for date and rate crops.

## Current Evidence Gates

Do not tune OCR defaults or replace EasyOCR until representative crop fixtures
exist under `tests/fixtures/ocr_crops/` with a `ground_truth.csv`. Speed changes
must be compared against the same 10-row live input with no increase in blank or
false-positive values.
