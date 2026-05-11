from __future__ import annotations

import json
import subprocess
import sys

from scripts.compare_run_reports import compare_reports


def make_report(rows, *, input_excel_path="source.xlsx"):
    return {
        "schema_version": 1,
        "input_excel_path": input_excel_path,
        "summary": {
            "processed_count": len(rows),
            "total_items": len(rows),
            "blank_date_count": sum(1 for row in rows if not row.get("date")),
            "blank_rate_count": sum(1 for row in rows if not row.get("rate")),
        },
        "rows": rows,
    }


def make_row(index, code, date="2026/05/08", rate="3.500", row_total_ms=1000.0):
    blank_fields = []
    if not date:
        blank_fields.append("date")
    if not rate:
        blank_fields.append("rate")
    return {
        "index": index,
        "code": code,
        "name": f"Name {index}",
        "date": date,
        "rate": rate,
        "status": "done",
        "failure_reason": "",
        "blank_fields": blank_fields,
        "timing_ms": {"row_total_ms": row_total_ms},
    }


def test_compare_reports_accepts_same_outputs_with_no_blank_regression():
    baseline = make_report([make_row(i, f"A{i:03d}", row_total_ms=1000 + i) for i in range(10)])
    candidate = make_report([make_row(i, f"A{i:03d}", row_total_ms=800 + i) for i in range(10)])

    report = compare_reports(baseline, candidate, min_rows=10)

    assert report["status"] == "ok"
    assert report["accepted"] is True
    assert report["gates"]["same_input"] is True
    assert report["gates"]["outputs_unchanged"] is True
    assert report["gates"]["blank_not_increased"] is True
    assert report["gates"]["failure_not_increased"] is True
    assert report["timing"]["p95_row_total_improved"] is True


def test_compare_reports_rejects_output_changes_and_blank_regressions():
    baseline = make_report([make_row(i, f"A{i:03d}") for i in range(10)])
    candidate_rows = [make_row(i, f"A{i:03d}") for i in range(10)]
    candidate_rows[3]["date"] = ""
    candidate_rows[3]["blank_fields"] = ["date"]
    candidate = make_report(candidate_rows)

    report = compare_reports(baseline, candidate, min_rows=10)

    assert report["status"] == "regression"
    assert report["accepted"] is False
    assert report["gates"]["outputs_unchanged"] is False
    assert report["gates"]["blank_not_increased"] is False
    assert report["output_changes"] == [
        {
            "index": 3,
            "code": "A003",
            "field": "date",
            "baseline": "2026/05/08",
            "candidate": "",
        }
    ]


def test_compare_reports_rejects_different_input_sequence():
    baseline = make_report([make_row(i, f"A{i:03d}") for i in range(10)])
    candidate_rows = [make_row(i, f"A{i:03d}") for i in range(10)]
    candidate_rows[5]["code"] = "B005"
    candidate = make_report(candidate_rows)

    report = compare_reports(baseline, candidate, min_rows=10)

    assert report["status"] == "regression"
    assert report["gates"]["same_input"] is False
    assert "row identity mismatch at index 5: A005/Name 5 != B005/Name 5" in report["errors"]


def test_compare_reports_rejects_different_input_workbook_path():
    baseline = make_report([make_row(i, f"A{i:03d}") for i in range(10)], input_excel_path=r"C:\runs\a.xlsx")
    candidate = make_report([make_row(i, f"A{i:03d}") for i in range(10)], input_excel_path=r"C:\runs\b.xlsx")

    report = compare_reports(baseline, candidate, min_rows=10)

    assert report["status"] == "regression"
    assert report["gates"]["same_input"] is False
    assert "input Excel path mismatch: C:\\runs\\a.xlsx != C:\\runs\\b.xlsx" in report["errors"]


def test_compare_reports_can_allow_different_input_workbook_path():
    baseline = make_report([make_row(i, f"A{i:03d}") for i in range(10)], input_excel_path=r"C:\runs\a.xlsx")
    candidate = make_report([make_row(i, f"A{i:03d}") for i in range(10)], input_excel_path=r"C:\runs\b.xlsx")

    report = compare_reports(baseline, candidate, min_rows=10, require_same_input=False)

    assert report["status"] == "ok"
    assert report["gates"]["same_input"] is True


def test_compare_reports_counts_status_failure_when_failure_reason_is_missing():
    baseline = make_report([make_row(i, f"A{i:03d}") for i in range(10)])
    candidate_rows = [make_row(i, f"A{i:03d}") for i in range(10)]
    candidate_rows[4].pop("failure_reason")
    candidate_rows[4]["status"] = "capture failed"
    candidate = make_report(candidate_rows)

    report = compare_reports(baseline, candidate, min_rows=10)

    assert report["status"] == "regression"
    assert report["gates"]["failure_not_increased"] is False
    assert report["candidate"]["failure_count"] == 1


def test_compare_reports_handles_bad_timing_values_without_crashing():
    baseline = make_report([make_row(i, f"A{i:03d}") for i in range(10)])
    candidate_rows = [make_row(i, f"A{i:03d}") for i in range(10)]
    candidate_rows[2]["timing_ms"]["row_total_ms"] = "n/a"
    candidate = make_report(candidate_rows)

    report = compare_reports(baseline, candidate, min_rows=10)

    assert report["status"] == "regression"
    assert report["accepted"] is False
    assert "candidate row 2 has non-numeric row_total_ms: n/a" in report["errors"]


def test_compare_reports_cli_writes_json_and_returns_failure(tmp_path):
    baseline = make_report([make_row(i, f"A{i:03d}") for i in range(9)])
    candidate = make_report([make_row(i, f"A{i:03d}") for i in range(9)])
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    output_json = tmp_path / "comparison.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/compare_run_reports.py",
            str(baseline_path),
            str(candidate_path),
            "--output-json",
            str(output_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["status"] == "regression"
    assert "minimum row count not met: baseline=9, candidate=9, required=10" in report["errors"]
