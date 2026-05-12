from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from checkocr2.excel_io import load_grid_rows
from checkocr2.models import CODE_COL
from scripts.prepare_live_smoke_workspace import (
    prepare_live_smoke_workspace,
    sha256_file,
)


def write_source_workbook(path: Path) -> None:
    pd.DataFrame(
        [
            {"code": "A001", "name": "Alpha"},
            {"code": "", "name": "Blank"},
            {"code": "A002", "name": "Beta"},
            {"code": "A003", "name": "Gamma"},
        ]
    ).to_excel(path, index=False)


def test_prepare_live_smoke_workspace_copies_rows_and_writes_manifest(tmp_path):
    source = tmp_path / "source.xlsx"
    write_source_workbook(source)
    source_hash = sha256_file(source)
    output_dir = tmp_path / "live_smoke"

    summary = prepare_live_smoke_workspace(
        source_excel=source,
        output_dir=output_dir,
        rows=2,
    )

    smoke_input = output_dir / "live_smoke_input.xlsx"
    manifest = output_dir / "live_smoke_manifest.json"
    assert smoke_input.exists()
    assert manifest.exists()
    assert sha256_file(source) == source_hash
    assert summary["status"] == "ready"
    assert summary["source_sha256"] == source_hash
    assert summary["smoke_input_sha256"] == sha256_file(smoke_input)
    assert summary["row_count"] == 2
    assert summary["rows"] == [
        {"code": "A001", "name": "Alpha"},
        {"code": "A002", "name": "Beta"},
    ]
    assert summary["expected_output_workbook"].endswith("live_smoke_input_updated.xlsx")
    assert summary["expected_run_report"].endswith("live_smoke_input_run_report.json")

    loaded_rows, missing = load_grid_rows(smoke_input)
    assert missing == []
    assert [row[CODE_COL] for row in loaded_rows] == ["A001", "A002"]
    assert json.loads(manifest.read_text(encoding="utf-8"))["source_sha256"] == source_hash


def test_prepare_live_smoke_workspace_rejects_unsafe_output_and_bad_names(tmp_path):
    source = tmp_path / "source.xlsx"
    write_source_workbook(source)

    with pytest.raises(ValueError, match="output_dir must be under"):
        prepare_live_smoke_workspace(
            source_excel=source,
            output_dir=Path("docs").resolve(),
        )

    with pytest.raises(ValueError, match="input_name must be a filename"):
        prepare_live_smoke_workspace(
            source_excel=source,
            output_dir=tmp_path / "live_smoke",
            input_name="../input.xlsx",
        )

    with pytest.raises(ValueError, match="manifest_name must end with .json"):
        prepare_live_smoke_workspace(
            source_excel=source,
            output_dir=tmp_path / "live_smoke",
            manifest_name="manifest.txt",
        )


def test_prepare_live_smoke_workspace_refuses_overwrite_and_empty_codes(tmp_path):
    source = tmp_path / "source.xlsx"
    write_source_workbook(source)
    output_dir = tmp_path / "live_smoke"
    prepare_live_smoke_workspace(source_excel=source, output_dir=output_dir)

    with pytest.raises(FileExistsError, match="live smoke output already exists"):
        prepare_live_smoke_workspace(source_excel=source, output_dir=output_dir)

    blank_source = tmp_path / "blank.xlsx"
    pd.DataFrame([{"code": "", "name": "Blank"}]).to_excel(blank_source, index=False)
    with pytest.raises(ValueError, match="no rows with a nonblank item code"):
        prepare_live_smoke_workspace(
            source_excel=blank_source,
            output_dir=tmp_path / "blank_smoke",
        )


def test_prepare_live_smoke_workspace_cli_writes_json(tmp_path):
    source = tmp_path / "source.xlsx"
    write_source_workbook(source)
    output_dir = tmp_path / "live_smoke"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_live_smoke_workspace.py",
            "--source-excel",
            str(source),
            "--output-dir",
            str(output_dir),
            "--rows",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["status"] == "ready"
    assert summary["row_count"] == 1
    assert (output_dir / "live_smoke_input.xlsx").exists()
