"""Path and filename helpers for CheckOCR2."""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path
from typing import Protocol


class LoggerLike(Protocol):
    def info(self, message: str) -> None: ...


def clean_folder_path(
    path: str | os.PathLike[str] | None,
    *,
    default: str = ".",
    platform_name: str | None = None,
    logger: LoggerLike | None = None,
) -> str:
    """Normalize local and UNC-style folder paths without checking existence."""

    if not path:
        return default

    system_name = platform_name or platform.system()
    cleaned_path = str(path).strip()
    original_path = cleaned_path
    is_unc = False
    prefix = ""

    if original_path.startswith("\\\\"):
        is_unc = True
        prefix = "\\\\"
        cleaned_path = original_path[2:]
    elif original_path.startswith("\\") and len(original_path) > 1:
        is_unc = True
        prefix = "\\\\"
        cleaned_path = original_path[1:]
        if logger:
            logger.info(f"단일 백슬래시 UNC 경로 정규화: {original_path} -> {prefix + cleaned_path}")
    elif original_path.startswith("//"):
        is_unc = True
        prefix = "\\\\"
        cleaned_path = original_path[2:]

    if is_unc:
        parts = [part for part in cleaned_path.split("/") if part]
        cleaned_path = prefix + "\\".join(parts)
    else:
        cleaned_path = cleaned_path.replace("\\", "/")
        while "//" in cleaned_path:
            cleaned_path = cleaned_path.replace("//", "/")

    cleaned_path = " ".join(cleaned_path.split())

    if system_name == "Windows" and is_unc:
        return cleaned_path
    if is_unc:
        return cleaned_path
    return os.path.normpath(cleaned_path)


def updated_workbook_path(output_dir: str | os.PathLike[str], input_file_path: str | None) -> Path:
    base_name = os.path.basename(input_file_path) if input_file_path else "ocr_results"
    output_name = os.path.splitext(base_name)[0] + "_updated.xlsx"
    return Path(output_dir) / output_name


def sanitize_filename(value: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", value)
