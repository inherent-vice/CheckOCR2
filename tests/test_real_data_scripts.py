from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from scripts.inventory_couponcheck_real_data import inventory_real_data
from scripts.prepare_real_data_workspace import (
    parse_days,
    prepare_real_data_workspace,
    sha256_file,
)


def create_day(source: Path, day: str, *, png_count: int = 2) -> Path:
    day_dir = source / f"List_CouponCheck_({day})"
    day_dir.mkdir(parents=True)
    (source / f"List_CouponCheck_({day}).xlsx").write_bytes(b"workbook-" + day.encode())
    (source / f"List_CouponCheck_({day})_updated.xlsx").write_bytes(
        b"updated-" + day.encode()
    )
    for index in range(png_count):
        Image.new("RGB", (10 + index, 20), "white").save(
            day_dir / f"KR{day}{index:02d}.png"
        )
    return day_dir


def test_inventory_real_data_reports_days_and_image_sizes(tmp_path):
    create_day(tmp_path, "20260513", png_count=2)
    create_day(tmp_path, "20260512", png_count=1)

    report = inventory_real_data(tmp_path, limit=1, sample_images=5)

    assert report["status"] == "ok"
    assert report["total_day_dirs"] == 2
    assert report["inventoried_day_count"] == 1
    assert report["days"][0]["day"] == "20260513"
    assert report["days"][0]["png_count"] == 2
    assert report["days"][0]["full_area_png_count"] == 2
    assert report["days"][0]["date_crop_count"] == 0
    assert report["days"][0]["rate_crop_count"] == 0
    assert report["days"][0]["missing_inputs"] == []
    assert report["summary"]["png_count_total"] == 2
    assert report["summary"]["image_size_counts"] == {"10x20": 1, "11x20": 1}


def test_prepare_real_data_workspace_copies_requested_days_with_hashes(tmp_path):
    source = tmp_path / "network"
    source.mkdir()
    create_day(source, "20260513", png_count=2)
    create_day(source, "20260512", png_count=1)
    output_dir = tmp_path / "workspace"

    manifest = prepare_real_data_workspace(
        source=source,
        output_dir=output_dir,
        days=["20260512"],
        allow_unsafe_output=True,
    )

    day = manifest["days"][0]
    assert manifest["status"] == "ready"
    assert day["day"] == "20260512"
    assert day["png_count"] == 1
    assert day["workbook"]["hash_match"] is True
    assert day["updated_workbook"]["hash_match"] is True
    assert day["images"][0]["hash_match"] is True
    copied_workbook = Path(day["workbook"]["destination"])
    source_workbook = source / "List_CouponCheck_(20260512).xlsx"
    assert copied_workbook.exists()
    assert sha256_file(source_workbook) == sha256_file(copied_workbook)
    assert (output_dir / "real_data_manifest.json").exists()


def test_prepare_real_data_workspace_rejects_bad_targets_and_overwrite(tmp_path):
    source = tmp_path / "network"
    source.mkdir()
    create_day(source, "20260513")

    with pytest.raises(ValueError, match="output_dir must not be inside"):
        prepare_real_data_workspace(
            source=source,
            output_dir=source / "local_copy",
            allow_unsafe_output=True,
        )

    with pytest.raises(ValueError, match="output_dir must be under"):
        prepare_real_data_workspace(
            source=source,
            output_dir=Path("docs").resolve(),
        )

    output_dir = tmp_path / "workspace"
    prepare_real_data_workspace(
        source=source,
        output_dir=output_dir,
        allow_unsafe_output=True,
    )
    with pytest.raises(FileExistsError, match="manifest already exists|day workspace"):
        prepare_real_data_workspace(
            source=source,
            output_dir=output_dir,
            allow_unsafe_output=True,
        )


def test_parse_days_validates_values():
    assert parse_days("20260513, 20260512") == ["20260513", "20260512"]
    with pytest.raises(ValueError, match="YYYYMMDD"):
        parse_days("2026-05-13")
    with pytest.raises(ValueError, match="at least one"):
        parse_days(",")


def test_real_data_inventory_cli_writes_json(tmp_path):
    source = tmp_path / "network"
    source.mkdir()
    create_day(source, "20260513")
    output_json = tmp_path / "inventory.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/inventory_couponcheck_real_data.py",
            "--source",
            str(source),
            "--output-json",
            str(output_json),
            "--limit",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(output_json.read_text(encoding="utf-8"))["status"] == "ok"


def test_prepare_real_data_workspace_cli_writes_manifest(tmp_path):
    source = tmp_path / "network"
    source.mkdir()
    create_day(source, "20260513")
    output_dir = tmp_path / "workspace"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_real_data_workspace.py",
            "--source",
            str(source),
            "--output-dir",
            str(output_dir),
            "--days",
            "20260513",
            "--allow-unsafe-output",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["status"] == "ready"
    assert (output_dir / "real_data_manifest.json").exists()

