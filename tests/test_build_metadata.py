from __future__ import annotations

import json

from checkocr2.build_metadata import (
    DIRECT_DEPENDENCIES,
    dependency_hash,
    forbidden_release_dependency_versions,
    format_build_metadata,
    generate_build_metadata,
    validate_release_dependency_environment,
    write_build_metadata,
)


def test_build_metadata_includes_versions_and_stable_hash():
    metadata_payload = generate_build_metadata(build_date="2026-05-08T00:00:00+00:00")

    assert metadata_payload["app_name"] == "CheckCaptureOCR_V6.1"
    assert metadata_payload["app_version"]
    assert metadata_payload["python_version"]
    assert set(DIRECT_DEPENDENCIES).issubset(metadata_payload["dependencies"])
    assert "opencv-python" not in DIRECT_DEPENDENCIES
    assert "opencv-python-headless" in DIRECT_DEPENDENCIES
    assert metadata_payload["dependency_hash"] == dependency_hash(metadata_payload["dependencies"])


def test_write_build_metadata_round_trips_json(tmp_path):
    output = tmp_path / "build_metadata.json"

    metadata_payload = write_build_metadata(output)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved == metadata_payload
    assert "Dependency hash:" in format_build_metadata(saved)


def test_forbidden_release_dependency_versions_filters_missing_packages(monkeypatch):
    versions = {
        "opencv-python": "4.10.0.84",
        "opencv-contrib-python": "not-installed",
    }

    monkeypatch.setattr(
        "checkocr2.build_metadata._distribution_version",
        lambda package_name: versions[package_name],
    )

    assert forbidden_release_dependency_versions() == {"opencv-python": "4.10.0.84"}


def test_validate_release_dependency_environment_rejects_gui_opencv(monkeypatch):
    monkeypatch.setattr(
        "checkocr2.build_metadata.forbidden_release_dependency_versions",
        lambda: {"opencv-python": "4.10.0.84"},
    )

    try:
        validate_release_dependency_environment()
    except RuntimeError as exc:
        assert "opencv-python==4.10.0.84" in str(exc)
    else:
        raise AssertionError("Expected contaminated release environment to be rejected")
