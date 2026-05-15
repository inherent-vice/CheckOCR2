from __future__ import annotations

import json

from checkocr2 import __version__
from checkocr2.build_metadata import (
    APP_PACKAGE_NAME,
    DIRECT_DEPENDENCIES,
    PADDLE_DEPENDENCIES,
    dependency_hash,
    forbidden_release_dependency_versions,
    format_build_metadata,
    generate_build_metadata,
    release_dependency_names,
    validate_release_dependency_environment,
    write_build_metadata,
)


def test_build_metadata_includes_versions_and_stable_hash():
    metadata_payload = generate_build_metadata(build_date="2026-05-08T00:00:00+00:00")

    assert metadata_payload["app_name"] == APP_PACKAGE_NAME
    assert metadata_payload["app_version"] == __version__
    assert metadata_payload["package_profile"] == "easyocr"
    assert metadata_payload["python_version"]
    assert set(DIRECT_DEPENDENCIES).issubset(metadata_payload["dependencies"])
    assert "opencv-python" not in DIRECT_DEPENDENCIES
    assert "opencv-python-headless" in DIRECT_DEPENDENCIES
    assert metadata_payload["dependency_hash"] == dependency_hash(metadata_payload["dependencies"])


def test_build_metadata_can_include_paddle_profile_dependencies():
    metadata_payload = generate_build_metadata(
        build_date="2026-05-08T00:00:00+00:00",
        include_paddle=True,
    )

    assert metadata_payload["package_profile"] == "paddle"
    assert set(PADDLE_DEPENDENCIES).issubset(metadata_payload["dependencies"])
    assert set(PADDLE_DEPENDENCIES).issubset(
        release_dependency_names(include_paddle=True)
    )


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


def test_validate_release_dependency_environment_allows_paddle_contrib_opencv(monkeypatch):
    versions = {
        "opencv-python": "not-installed",
        "paddleocr": "3.5.0",
        "paddlepaddle": "3.3.1",
    }

    def fake_distribution_version(package_name: str) -> str:
        return versions.get(package_name, "not-installed")

    monkeypatch.setattr(
        "checkocr2.build_metadata._distribution_version",
        fake_distribution_version,
    )
    monkeypatch.setattr(
        "checkocr2.build_metadata.forbidden_release_dependency_versions",
        lambda package_names=("opencv-python",): {
            package_name: versions[package_name]
            for package_name in package_names
            if versions.get(package_name) != "not-installed"
        },
    )

    validate_release_dependency_environment(allow_paddle=True)


def test_validate_release_dependency_environment_requires_paddle_runtime(monkeypatch):
    monkeypatch.setattr(
        "checkocr2.build_metadata.forbidden_release_dependency_versions",
        lambda package_names=("opencv-python",): {},
    )
    monkeypatch.setattr(
        "checkocr2.build_metadata._distribution_version",
        lambda _package_name: "not-installed",
    )

    try:
        validate_release_dependency_environment(allow_paddle=True)
    except RuntimeError as exc:
        assert "Missing: paddleocr, paddlepaddle" in str(exc)
    else:
        raise AssertionError("Expected missing Paddle runtime to be rejected")
