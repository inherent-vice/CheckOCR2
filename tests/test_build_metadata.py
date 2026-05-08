from __future__ import annotations

import json

from checkocr2.build_metadata import (
    DIRECT_DEPENDENCIES,
    dependency_hash,
    format_build_metadata,
    generate_build_metadata,
    write_build_metadata,
)


def test_build_metadata_includes_versions_and_stable_hash():
    metadata_payload = generate_build_metadata(build_date="2026-05-08T00:00:00+00:00")

    assert metadata_payload["app_name"] == "CheckCaptureOCR_V6.1"
    assert metadata_payload["app_version"]
    assert metadata_payload["python_version"]
    assert set(DIRECT_DEPENDENCIES).issubset(metadata_payload["dependencies"])
    assert metadata_payload["dependency_hash"] == dependency_hash(metadata_payload["dependencies"])


def test_write_build_metadata_round_trips_json(tmp_path):
    output = tmp_path / "build_metadata.json"

    metadata_payload = write_build_metadata(output)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved == metadata_payload
    assert "Dependency hash:" in format_build_metadata(saved)
