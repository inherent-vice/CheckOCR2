from __future__ import annotations

from checkocr2.ui.file_dialogs import (
    normalize_initial_output_path,
    output_folder_for_input_file,
    output_folder_initial_dir,
)


def test_output_folder_for_input_file_uses_parent_and_cleaner():
    seen = []

    def clean(path: str) -> str:
        seen.append(path)
        return path.replace("\\", "/")

    assert (
        output_folder_for_input_file(r"C:\input\sample.xlsx", clean_folder=clean)
        == "C:/input"
    )
    assert seen == [r"C:\input"]


def test_normalize_initial_output_path_preserves_unc_and_normalizes_single_slash():
    assert normalize_initial_output_path(r"\server\share") == r"\\server\share"
    assert normalize_initial_output_path(r"\\server\share") == r"\\server\share"
    assert normalize_initial_output_path("  C:/Output  ") == "C:/Output"


def test_output_folder_initial_dir_uses_existing_current_path():
    existing = {r"C:\Output"}

    assert (
        output_folder_initial_dir(
            r"C:\Output",
            exists=existing.__contains__,
        )
        == r"C:\Output"
    )


def test_output_folder_initial_dir_falls_back_to_existing_unc_share():
    existing = {r"\\server\share"}

    assert (
        output_folder_initial_dir(
            r"\\server\share\nested\output",
            exists=existing.__contains__,
        )
        == r"\\server\share"
    )


def test_output_folder_initial_dir_returns_none_for_missing_path():
    assert (
        output_folder_initial_dir(
            r"\\server\missing\folder", exists=lambda _path: False
        )
        is None
    )
    assert output_folder_initial_dir("   ", exists=lambda _path: True) is None
