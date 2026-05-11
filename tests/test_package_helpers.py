from __future__ import annotations

import json

from PIL import Image

from checkocr2.image_processing import screenshot_region, upscale_image
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
from checkocr2.ocr_text import clean_date_text, clean_rate_text
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


def test_ocr_text_helpers_match_existing_normalization():
    assert clean_date_text("2024-05-01") == "2024/05/01"
    assert clean_date_text("24.05.01") == "2024/05/01"
    assert clean_rate_text("3.5%") == "3.500"
    assert clean_rate_text("12,500") == "12.500"
    assert clean_rate_text("10·25") == "10.250"


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
