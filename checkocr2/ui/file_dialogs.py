"""File and folder dialog helper logic for the Tk shell."""

from __future__ import annotations

import os
from collections.abc import Callable


def output_folder_for_input_file(
    file_path: str,
    *,
    clean_folder: Callable[[str], str],
) -> str:
    return clean_folder(os.path.dirname(file_path))


def normalize_initial_output_path(path: str) -> str:
    current_path = path.strip()
    if current_path.startswith("\\") and not current_path.startswith("\\\\"):
        return "\\" + current_path
    return current_path


def output_folder_initial_dir(
    current_path: str,
    *,
    exists: Callable[[str], bool] = os.path.exists,
) -> str | None:
    normalized_path = normalize_initial_output_path(current_path)
    if not normalized_path:
        return None

    if exists(normalized_path):
        return normalized_path

    if normalized_path.startswith("\\\\"):
        path_parts = normalized_path.split("\\")
        if len(path_parts) >= 4:
            server_share = "\\\\" + path_parts[2] + "\\" + path_parts[3]
            if exists(server_share):
                return server_share

    return None
