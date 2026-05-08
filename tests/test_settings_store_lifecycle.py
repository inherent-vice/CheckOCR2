from __future__ import annotations

import json

import pytest

from checkocr2.exceptions import SettingsError
from checkocr2.settings import DEFAULT_SETTINGS, SettingsStore


def test_settings_store_merges_missing_keys_and_preserves_example_file(tmp_path):
    settings_file = tmp_path / "user" / "settings.json"
    settings_file.parent.mkdir()
    settings_file.write_text(
        json.dumps({"advanced": {"ui_theme": "green_nature"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    example_file = tmp_path / "settings.example.json"
    example_file.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False), encoding="utf-8")
    before = example_file.read_text(encoding="utf-8")

    store = SettingsStore(settings_file, legacy_settings_file=None)

    assert store.get_advanced("ui_theme") == "green_nature"
    assert store.get_advanced("skip_kbp_code") is True
    assert store.data["delays"] == DEFAULT_SETTINGS["delays"]
    assert example_file.read_text(encoding="utf-8") == before


def test_settings_store_rejects_corrupt_json(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("{not-json", encoding="utf-8")

    with pytest.raises(SettingsError, match="설정 로드 오류"):
        SettingsStore(settings_file, legacy_settings_file=None)


def test_settings_store_preset_and_current_lifecycle(tmp_path):
    settings_file = tmp_path / "settings.json"
    store = SettingsStore(settings_file, legacy_settings_file=None)
    preset = {
        "click_point": [1, 2],
        "all_area": [0, 0, 100, 100],
        "date_area": [1, 1, 10, 10],
        "rate_area": [11, 1, 20, 10],
        "delays": {"paste": 0.1, "loading": 0.2},
        "save_detail_images": False,
        "advanced": {"skip_kbp_code": False},
    }

    store.save_preset("fast", preset)

    assert store.get_preset_names() == ["fast"]
    applied = store.apply_preset("fast")
    assert applied is not None
    assert applied["click_point"] == [1, 2]
    assert applied["save_detail_images"] is False

    current = {"input_excel_path": "input.xlsx", "output_folder_path": "out"}
    store.save_current_settings(current)
    assert store.get_current_settings() == current

    store.delete_preset("fast")
    assert store.get_preset_names() == []
    saved = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved["current"] == current
