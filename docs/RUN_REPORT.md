# OCR Run Report

Each OCR run writes a JSON report next to the exported Excel workbook:

```text
<output folder>/<input workbook stem>_run_report.json
```

For example, processing `checks.xlsx` into `E:\out` creates
`E:\out\checks_updated.xlsx` and `E:\out\checks_run_report.json`.

## Contents

- `started_at` and `completed_at`: local timestamps for the OCR run.
- `summary`: processed count, total rows, stop state, blank date/rate counts,
  status counts, output workbook path, and export timing.
- `rows`: one entry per grid row with code, name, extracted date/rate, final
  status, blank fields, failure reason, and timing data.
- `timing_ms`: per-row stages such as copy, click, paste wait, load wait,
  screenshot capture, image save, OCR preprocess, OCR date/rate, parse, update,
  and total row time.
- `errors`: workflow or export issues that occurred after the run report was
  initialized.

## Use

Use the report to compare runs before changing OCR settings, fixed waits, or
capture regions. Do not reduce paste/load delays until the same 10-row live
input has a stable report with no increase in blank or false-positive values.
