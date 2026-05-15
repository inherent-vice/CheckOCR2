from __future__ import annotations

import json
from types import MappingProxyType

import pytest
from PIL import Image

from checkocr2.image_processing import (
    cleanup_temp_ocr_image,
    screenshot_region,
    upscale_image,
    upscale_image_source,
)
from checkocr2.models import (
    CODE_COL,
    DATE_COL,
    NAME_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_WAITING,
    OcrRow,
    Region,
)
from checkocr2.ocr_field_extraction import select_field_text_from_ocr_results
from checkocr2.ocr_text import clean_date_text, clean_rate_text, is_valid_date_format
from checkocr2.paths import clean_folder_path, sanitize_filename, updated_workbook_path
from checkocr2.settings import SettingsStore


def test_ocr_row_round_trips_legacy_grid_dict():
    row = OcrRow(code="KR1", name="Name", date="2026/05/08", rate="3.500")

    as_dict = row.to_dict()

    assert as_dict == {
        CODE_COL: "KR1",
        NAME_COL: "Name",
        DATE_COL: "2026/05/08",
        RATE_COL: "3.500",
        STATUS_COL: STATUS_WAITING,
    }
    assert OcrRow.from_dict(as_dict) == row


def test_ocr_row_from_dict_accepts_read_only_mapping():
    row = MappingProxyType(
        {
            CODE_COL: "KR2",
            NAME_COL: "ReadOnly",
            DATE_COL: "2026/05/09",
            RATE_COL: "4.250",
            STATUS_COL: STATUS_WAITING,
        }
    )

    assert OcrRow.from_dict(row) == OcrRow(
        code="KR2",
        name="ReadOnly",
        date="2026/05/09",
        rate="4.250",
    )


def test_path_helpers_preserve_windows_unc_behavior():
    assert clean_folder_path(r"\server\share\folder", platform_name="Windows") == r"\\server\share\folder"
    assert clean_folder_path("//server/share/folder", platform_name="Windows") == r"\\server\share\folder"
    local_path = clean_folder_path(r"C:\Temp\CheckOCR2", platform_name="Windows").replace("\\", "/")
    assert local_path.endswith("C:/Temp/CheckOCR2")
    assert clean_folder_path(None, default="fallback") == "fallback"
    assert sanitize_filename('A/B:C*D?"E<>|') == "A_B_C_D__E___"
    assert updated_workbook_path("out", r"C:\input\source.xlsx").as_posix() == "out/source_updated.xlsx"


def test_image_helpers_upscale_and_validate_regions():
    image = Image.new("RGB", (10, 6), "white")

    assert upscale_image(image, enabled=False, factor=3).size == (10, 6)
    assert upscale_image(image, enabled=True, factor=2.5, method="BICUBIC").size == (25, 15)
    assert screenshot_region(Region(1, 2, 11, 8)) == (1, 2, 10, 6)


@pytest.mark.parametrize("method", ["LANCZOS", "BICUBIC", "BILINEAR", "UNKNOWN"])
def test_upscale_image_accepts_supported_methods_and_unknown_fallback(method):
    image = Image.new("RGB", (10, 6), "white")

    result = upscale_image(image, enabled=True, factor=2, method=method)

    assert result.size == (20, 12)


def test_upscale_image_source_reports_sizes_and_upscaled_flag(tmp_path):
    image = Image.new("RGB", (10, 6), "white")
    image_path = tmp_path / "crop.png"
    image.save(image_path)

    disabled = upscale_image_source(image, enabled=False, factor=3)
    from_path = upscale_image_source(
        str(image_path), enabled=True, factor=2, method="NEAREST"
    )

    assert disabled.image is image
    assert disabled.original_size == (10, 6)
    assert disabled.new_size == (10, 6)
    assert disabled.was_upscaled is False
    assert from_path.original_size == (10, 6)
    assert from_path.new_size == (20, 12)
    assert from_path.was_upscaled is True


def test_cleanup_temp_ocr_image_removes_legacy_date_and_rate_paths(tmp_path):
    date_path = tmp_path / "ABC_date.png"
    rate_path = tmp_path / "ABC_rate.png"
    date_path.write_text("date", encoding="utf-8")
    rate_path.write_text("rate", encoding="utf-8")

    date_result = cleanup_temp_ocr_image(str(date_path), save_details=False, field_name="날짜")
    rate_result = cleanup_temp_ocr_image(str(rate_path), save_details=False, field_name="금리")

    assert date_result.removed is True
    assert date_result.log_event == (
        f"임시 날짜 이미지 파일 삭제: {date_path}",
        "DEBUG",
    )
    assert not date_path.exists()
    assert rate_result.removed is True
    assert rate_result.log_event == (
        f"임시 금리 이미지 파일 삭제: {rate_path}",
        "DEBUG",
    )
    assert not rate_path.exists()


def test_cleanup_temp_ocr_image_ignores_non_temp_paths_and_detail_saves(tmp_path):
    detail_path = tmp_path / "ABC_date.png"
    other_path = tmp_path / "ABC_other.png"
    detail_path.write_text("date", encoding="utf-8")
    other_path.write_text("other", encoding="utf-8")

    assert cleanup_temp_ocr_image(
        str(detail_path), save_details=True, field_name="날짜"
    ).log_event is None
    assert cleanup_temp_ocr_image(
        str(other_path), save_details=False, field_name="날짜"
    ).log_event is None
    assert cleanup_temp_ocr_image(
        object(), save_details=False, field_name="날짜"
    ).log_event is None
    assert detail_path.exists()
    assert other_path.exists()


def test_cleanup_temp_ocr_image_reports_remove_failure():
    result = cleanup_temp_ocr_image(
        "ABC_date.png",
        save_details=False,
        field_name="날짜",
        exists_func=lambda _path: True,
        remove_func=lambda _path: (_ for _ in ()).throw(OSError("denied")),
    )

    assert result.removed is False
    assert result.log_event == (
        "임시 날짜 이미지 파일 삭제 실패: denied",
        "WARNING",
    )


def test_ocr_text_helpers_match_existing_normalization():
    assert clean_date_text("2024-05-01") == "2024/05/01"
    assert clean_date_text("24.05.01") == "2024/05/01"
    assert clean_date_text("2026/05/05 D0D") == "2026/05/05"
    assert clean_date_text("202605050") == "2026/05/05"
    assert clean_rate_text("3.5%") == "3.5000"
    assert clean_rate_text("12,500") == "12.5000"
    assert clean_rate_text("10·25") == "10.2500"
    assert clean_rate_text("3.5%", 3) == "3.500"


def test_ocr_rate_helpers_cover_digit_only_and_trailing_dot_cases():
    assert clean_rate_text("4.") == "4.0000"
    assert clean_rate_text("7") == "7.0000"
    assert clean_rate_text("274000") == "2.7400"
    assert clean_rate_text("28900") == "2.8900"
    assert clean_rate_text("7", 2) == "7.00"


def test_select_field_text_from_ocr_results_prefers_first_valid_full_image_field():
    results = [
        "표준코드",
        "KR310206GFA2",
        "–",
        "2026/06/13",
        "2.77000",
        "발행일",
        "2025.10.13",
        "월",
        "2",
    ]

    assert select_field_text_from_ocr_results(results, "date") == "2026/06/13"
    assert select_field_text_from_ocr_results(results, "rate") == "2.7700"


def test_ocr_date_validation_rejects_non_calendar_dates():
    assert is_valid_date_format("2024/02/29") is True
    assert is_valid_date_format("2024/02/30") is False
    assert is_valid_date_format("2024/13/01") is False


def test_settings_store_migrates_legacy_file_to_user_path(tmp_path):
    legacy = tmp_path / "settings.json"
    target = tmp_path / "user" / "settings.json"
    legacy.write_text(
        json.dumps(
            {
                "advanced": {"ui_theme": "orange_warm"},
                "current": {"input_excel_path": "input.xlsx"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = SettingsStore(target, legacy_settings_file=legacy)

    assert store.get_advanced("ui_theme") == "orange_warm"
    assert store.get_current_settings()["input_excel_path"] == "input.xlsx"
    assert target.exists()
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["advanced"]["skip_kbp_code"] is True


def test_settings_store_keeps_legacy_values_when_user_path_write_fails(tmp_path):
    legacy = tmp_path / "settings.json"
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not a directory", encoding="utf-8")
    target = blocked_parent / "settings.json"
    legacy.write_text(
        json.dumps({"advanced": {"ui_theme": "green_nature"}}, ensure_ascii=False),
        encoding="utf-8",
    )

    store = SettingsStore(target, legacy_settings_file=legacy)

    assert store.get_advanced("ui_theme") == "green_nature"
    assert store.migration_warning
