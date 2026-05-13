from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook
from PIL import Image

from scripts.extract_real_data_ocr_fixtures import (
    extract_real_data_ocr_fixtures,
    parse_roi,
)


def create_real_day(tmp_path: Path) -> Path:
    day_dir = tmp_path / "20260513"
    image_dir = day_dir / "images"
    image_dir.mkdir(parents=True)
    workbook = Workbook()
    ws = workbook.active
    ws.append(["종목코드", "종목명", "날짜", "금리", "상태"])
    ws.append(["KRTEST001", "테스트1", "2026/06/13", "2.770", "완료"])
    ws.append(["KRTEST002", "테스트2", None, None, "완료"])
    workbook.save(day_dir / "List_CouponCheck_(20260513)_updated.xlsx")
    Image.new("RGB", (100, 80), "white").save(image_dir / "KRTEST001.png")
    Image.new("RGB", (100, 80), "white").save(image_dir / "KRTEST002.png")
    return day_dir


def test_parse_roi_validates_fraction_box():
    assert parse_roi("0.1,0,0.9,0.5", "date") == (0.1, 0.0, 0.9, 0.5)
    with pytest.raises(ValueError, match="four"):
        parse_roi("0,1", "date")
    with pytest.raises(ValueError, match="fractions"):
        parse_roi("0.9,0,0.1,1", "date")


def test_extract_real_data_ocr_fixtures_writes_crops_and_ground_truth(tmp_path):
    day_dir = create_real_day(tmp_path)
    output_dir = tmp_path / "fixtures"

    summary = extract_real_data_ocr_fixtures(
        day_dir=day_dir,
        output_dir=output_dir,
        date_roi="0,0,0.5,0.5",
        rate_roi="0.5,0,1,0.5",
        layout="cropped",
        allow_unsafe_output=True,
    )

    assert summary["status"] == "ready"
    assert summary["total_cases"] == 2
    assert summary["field_counts"] == {"date": 1, "rate": 1}
    assert summary["skipped_blank_expected_count"] == 2
    csv_text = (output_dir / "ground_truth.csv").read_text(encoding="utf-8-sig")
    assert "KRTEST001_date.png" in csv_text
    assert "expected_from_updated_workbook" in csv_text
    date_crop = output_dir / "0001_20260513_KRTEST001_date.png"
    assert date_crop.exists()
    assert Image.open(date_crop).size == (50, 40)
    manifest = json.loads((output_dir / "fixture_manifest.json").read_text(encoding="utf-8"))
    assert manifest["total_cases"] == 2


def test_extract_real_data_ocr_fixtures_rejects_unsafe_output(tmp_path):
    day_dir = create_real_day(tmp_path)

    with pytest.raises(ValueError, match="output_dir must be under"):
        extract_real_data_ocr_fixtures(day_dir=day_dir, output_dir=Path("docs").resolve())


def test_extract_real_data_ocr_fixtures_cli(tmp_path):
    day_dir = create_real_day(tmp_path)
    output_dir = tmp_path / "fixtures"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/extract_real_data_ocr_fixtures.py",
            "--day-dir",
            str(day_dir),
            "--output-dir",
            str(output_dir),
            "--date-roi",
            "0,0,0.5,0.5",
            "--rate-roi",
            "0.5,0,1,0.5",
            "--layout",
            "cropped",
            "--allow-unsafe-output",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "ready"
    assert (output_dir / "ground_truth.csv").exists()
