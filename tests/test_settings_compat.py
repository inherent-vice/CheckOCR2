from __future__ import annotations

from datetime import datetime

from checkocr2 import settings_compat
from checkocr2.exceptions import SettingsError
from checkocr2.settings import DEFAULT_SETTINGS


def test_unified_settings_manager_save_preset_adds_created_at(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    manager = settings_compat.UnifiedSettingsManager()
    preset = {
        "click_point": [1, 2],
        "all_area": [0, 0, 100, 100],
        "date_area": [1, 1, 10, 10],
        "rate_area": [11, 1, 20, 10],
        "delays": {"paste": 0.1, "loading": 0.2},
        "save_detail_images": False,
        "advanced": {"skip_kbp_code": False},
    }

    manager.save_preset("fast", preset)

    saved = manager.apply_preset("fast")
    assert saved is not None
    assert saved["click_point"] == [1, 2]
    assert saved["save_detail_images"] is False
    assert datetime.fromisoformat(saved["created_at"])


def test_unified_settings_manager_falls_back_to_defaults_on_settings_error(
    monkeypatch,
    capsys,
):
    def fail_init(self):
        raise SettingsError("bad settings")

    monkeypatch.setattr(settings_compat.SettingsStore, "__init__", fail_init)

    manager = settings_compat.UnifiedSettingsManager()

    assert "설정 로드 오류: bad settings" in capsys.readouterr().out
    assert manager.settings_file == "settings.json"
    assert manager.legacy_settings_file == "settings.json"
    assert manager.data == DEFAULT_SETTINGS
    assert manager.data is not DEFAULT_SETTINGS
