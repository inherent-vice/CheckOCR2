"""Build and dependency metadata helpers for packaged releases."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from importlib import metadata, resources
from pathlib import Path
from typing import Any

from . import __version__

BUILD_METADATA_FILENAME = "build_metadata.json"
DIRECT_DEPENDENCIES = (
    "easyocr",
    "numpy",
    "opencv-python",
    "openpyxl",
    "pandas",
    "Pillow",
    "PyAutoGUI",
    "pyperclip",
    "torch",
    "torchvision",
)


def _distribution_version(package_name: str) -> str:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return "not-installed"


def dependency_versions(package_names: tuple[str, ...] = DIRECT_DEPENDENCIES) -> dict[str, str]:
    return {package_name: _distribution_version(package_name) for package_name in package_names}


def dependency_hash(dependencies: dict[str, str]) -> str:
    payload = json.dumps(dependencies, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def generate_build_metadata(build_date: str | None = None) -> dict[str, Any]:
    dependencies = dependency_versions()
    return {
        "app_name": "CheckCaptureOCR_V6.1",
        "app_version": __version__,
        "build_date": build_date or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "dependencies": dependencies,
        "dependency_hash": dependency_hash(dependencies),
    }


def write_build_metadata(path: str | Path) -> dict[str, Any]:
    metadata_payload = generate_build_metadata()
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata_payload


def load_build_metadata() -> dict[str, Any]:
    try:
        resource = resources.files("checkocr2").joinpath(BUILD_METADATA_FILENAME)
        if resource.is_file():
            return json.loads(resource.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError, json.JSONDecodeError, OSError):
        pass
    return generate_build_metadata(build_date="runtime")


def format_build_metadata(metadata_payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Version: {metadata_payload.get('app_version', 'unknown')}",
            f"Build date: {metadata_payload.get('build_date', 'unknown')}",
            f"Python: {metadata_payload.get('python_version', 'unknown')}",
            f"Dependency hash: {metadata_payload.get('dependency_hash', 'unknown')}",
        ]
    )
