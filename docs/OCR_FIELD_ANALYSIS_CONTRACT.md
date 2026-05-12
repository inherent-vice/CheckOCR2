# OCR Field Analysis Contract

Date: 2026-05-12

## Purpose

`checkocr2/ocr_field_analysis.py` owns the pure date/rate OCR field decision
logic. It converts raw EasyOCR text into the value stored in the grid and the
legacy debug-log messages that the Tk workflow must still emit.

This module is intentionally Tk-free. It must not import the app, queues,
messageboxes, screen automation, Excel helpers, or EasyOCR. The legacy
`OCRWorkflowManager` remains the compatibility adapter that turns
`OcrFieldAnalysis.log_events` into queue events.

## Runtime Boundary

```text
EasyOCR raw text
  -> analyze_date_field() / analyze_rate_field()
  -> OcrFieldAnalysis(value, log_events)
  -> OCRWorkflowManager enqueues ("log", message, level)
  -> Tk queue dispatcher writes the log panel
```

The manager wrapper must preserve:

- Queue payload shape: `("log", message, level)`.
- Log event ordering exactly as returned by the helper.
- Return value exactly equal to `result.value`.
- Default field labels: `날짜` and `금리`.
- `raw_text: str | None` compatibility; `None` is treated as empty OCR text.
- No direct cleaning, validation, or formatting inside the manager wrapper.

## Value And Log Rules

Empty, whitespace, or `None` input returns an empty value and one `DEBUG` log:

```text
[<field>] 텍스트가 비어있습니다.
```

Valid date input logs the raw text, logs the normalized date, and returns the
normalized value:

```text
[날짜] 원본 텍스트: '2026-05-08'
[날짜] 유효한 날짜: '2026/05/08'
```

Invalid date input logs the raw text, logs the failed normalized candidate, and
returns an empty value:

```text
[날짜] 유효하지 않은 날짜 형식: '<cleaned>' (원본: '<raw>')
```

Date validity is calendar-aware, not only format-aware. A normalized candidate
such as `2026/02/30` is rejected through this invalid-date path.

Valid rate input logs the raw text, logs the normalized rate, and returns the
normalized value:

```text
[금리] 원본 텍스트: '3.5%'
[금리] 유효한 금리: '3.500'
```

Invalid rate input logs the raw text, logs the failed normalized candidate, and
returns an empty value:

```text
[금리] 유효하지 않은 금리 형식: '<cleaned>' (원본: '<raw>')
```

## Verification

Focused checks for this boundary:

```powershell
python -m ruff check check_capture_ocr.py checkocr2\ocr_field_analysis.py tests\test_ocr_field_analysis.py tests\test_ocr_workflow_manager.py
python -m mypy --follow-imports=skip checkocr2\ocr_field_analysis.py tests\test_ocr_field_analysis.py
python -m pytest tests\test_ocr_field_analysis.py tests\test_ocr_workflow_manager.py tests\test_package_helpers.py --basetemp $env:TEMP\checkocr2-ocr-field-focused
```

Before release or commit, also run the full source gate, source GUI smoke, clean
PyInstaller build, and real package smoke listed in
`docs/IMPLEMENTATION_STATUS.md`.
