"""Build and dependency metadata helpers for packaged releases."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import UTC, datetime
from importlib import metadata, resources
from pathlib import Path
from typing import Any

from . import __version__

BUILD_METADATA_FILENAME = "build_metadata.json"
PADDLE_PACKAGE_ENV = "CHECKOCR2_PACKAGE_PADDLE"
FORBIDDEN_RELEASE_DEPENDENCIES = ("opencv-python", "opencv-contrib-python")
DIRECT_DEPENDENCIES = (
    "easyocr",
    "numpy",
    "opencv-python-headless",
    "openpyxl",
    "pandas",
    "Pillow",
    "PyAutoGUI",
    "pyperclip",
    "torch",
    "torchvision",
)
PADDLE_DEPENDENCIES = (
    "paddleocr",
    "paddlepaddle",
    "opencv-python",
    "opencv-contrib-python",
)


def _distribution_version(package_name: str) -> str:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return "not-installed"


def dependency_versions(package_names: tuple[str, ...] = DIRECT_DEPENDENCIES) -> dict[str, str]:
    return {package_name: _distribution_version(package_name) for package_name in package_names}


def forbidden_release_dependency_versions(
    package_names: tuple[str, ...] = FORBIDDEN_RELEASE_DEPENDENCIES,
) -> dict[str, str]:
    return {
        package_name: version
        for package_name in package_names
        if (version := _distribution_version(package_name)) != "not-installed"
    }


def paddle_package_enabled() -> bool:
    return os.environ.get(PADDLE_PACKAGE_ENV, "").strip() == "1"


def release_dependency_names(*, include_paddle: bool = False) -> tuple[str, ...]:
    names = list(DIRECT_DEPENDENCIES)
    if include_paddle:
        for package_name in PADDLE_DEPENDENCIES:
            if package_name not in names:
                names.append(package_name)
    return tuple(names)


def validate_release_dependency_environment(*, allow_paddle: bool | None = None) -> None:
    paddle_enabled = paddle_package_enabled() if allow_paddle is None else allow_paddle
    if paddle_enabled:
        forbidden_dependencies = forbidden_release_dependency_versions(("opencv-python",))
    else:
        forbidden_dependencies = forbidden_release_dependency_versions()
    if forbidden_dependencies:
        formatted = ", ".join(
            f"{package_name}=={version}" for package_name, version in forbidden_dependencies.items()
        )
        package_profile = "Paddle" if paddle_enabled else "EasyOCR"
        raise RuntimeError(
            f"{package_profile} release package builds require a clean environment without "
            f"forbidden OpenCV distributions. Found: {formatted}. Build from a fresh venv with "
            "requirements-build.txt."
        )
    if paddle_enabled:
        missing_paddle_dependencies = [
            package_name
            for package_name in ("paddleocr", "paddlepaddle")
            if _distribution_version(package_name) == "not-installed"
        ]
        if missing_paddle_dependencies:
            missing = ", ".join(missing_paddle_dependencies)
            raise RuntimeError(
                "Paddle release package builds require PaddleOCR runtime dependencies. "
                f"Missing: {missing}. Install paddlepaddle and requirements-paddle.txt first."
            )


def dependency_hash(dependencies: dict[str, str]) -> str:
    payload = json.dumps(dependencies, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def generate_build_metadata(
    build_date: str | None = None,
    *,
    include_paddle: bool | None = None,
) -> dict[str, Any]:
    paddle_enabled = paddle_package_enabled() if include_paddle is None else include_paddle
    dependencies = dependency_versions(release_dependency_names(include_paddle=paddle_enabled))
    return {
        "app_name": "CheckCaptureOCR_V6.1",
        "app_version": __version__,
        "package_profile": "paddle" if paddle_enabled else "easyocr",
        "build_date": build_date or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "dependencies": dependencies,
        "dependency_hash": dependency_hash(dependencies),
    }


def write_build_metadata(
    path: str | Path,
    *,
    include_paddle: bool | None = None,
) -> dict[str, Any]:
    metadata_payload = generate_build_metadata(include_paddle=include_paddle)
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
