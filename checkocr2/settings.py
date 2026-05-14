"""Settings storage and migration helpers."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .exceptions import SettingsError

APP_NAME = "CheckOCR2"

DEFAULT_SETTINGS: dict[str, Any] = {
    "click_point": [340, 165],
    "all_area": [15, 200, 1845, 870],
    "date_area": [826, 88, 1064, 127],
    "rate_area": [1069, 89, 1326, 126],
    "delays": {"paste": 0.5, "loading": 2.5},
    "advanced": {
        "ocr_languages": ["ko", "en"],
        "ocr_engine": "paddle",
        "ocr_max_attempts": 1,
        "ocr_detail_level": 0,
        "click_interval": 0.1,
        "min_date_confidence": 0.0,
        "min_rate_confidence": 0.0,
        "rate_decimal_places": 3,
        "ui_theme": "modern_blue",
        "skip_kbp_code": True,
        "upscaling_enabled": True,
        "upscaling_factor": 2.0,
        "upscaling_method": "LANCZOS",
    },
    "presets": {},
    "current": {},
}


def user_settings_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME / "settings.json"
    return Path.home() / ".checkocr2" / "settings.json"


def deep_merge_defaults(data: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    result = copy.deepcopy(defaults or DEFAULT_SETTINGS)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge_defaults(value, result[key])
        else:
            result[key] = value
    return result


class SettingsStore:
    """JSON-backed settings store with local user-path migration support."""

    def __init__(
        self,
        settings_file: str | os.PathLike[str] | None = None,
        *,
        legacy_settings_file: str | os.PathLike[str] | None = "settings.json",
    ):
        self.settings_file = str(settings_file or user_settings_path())
        self.legacy_settings_file = str(legacy_settings_file) if legacy_settings_file else None
        self.migration_warning: str | None = None
        self.data = self.load_settings()

    def load_settings(self) -> dict[str, Any]:
        path = Path(self.settings_file)
        legacy_path = Path(self.legacy_settings_file) if self.legacy_settings_file else None

        load_path = path
        if not path.exists() and legacy_path and legacy_path.exists():
            load_path = legacy_path

        if load_path.exists():
            try:
                with load_path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise SettingsError(f"Settings root must be an object: {load_path}")
                merged = deep_merge_defaults(loaded)
                if load_path != path:
                    self.data = merged
                    try:
                        self.save_settings()
                    except SettingsError as exc:
                        self.migration_warning = str(exc)
                return merged
            except (OSError, json.JSONDecodeError, SettingsError) as exc:
                raise SettingsError(f"설정 로드 오류: {load_path}: {exc}") from exc

        return copy.deepcopy(DEFAULT_SETTINGS)

    def save_settings(self) -> None:
        path = Path(self.settings_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            raise SettingsError(f"설정 저장 오류: {path}: {exc}") from exc

    def save_preset(self, name: str, settings: dict[str, Any]) -> None:
        self.data.setdefault("presets", {})[name] = {
            "click_point": settings["click_point"],
            "all_area": settings["all_area"],
            "date_area": settings["date_area"],
            "rate_area": settings["rate_area"],
            "delays": settings["delays"],
            "save_detail_images": settings.get("save_detail_images", True),
            "advanced": settings.get("advanced", {}),
            "created_at": settings.get("created_at"),
        }
        self.save_settings()

    def get_preset_names(self) -> list[str]:
        return list(self.data.setdefault("presets", {}).keys())

    def apply_preset(self, name: str) -> dict[str, Any] | None:
        return self.data.setdefault("presets", {}).get(name)

    def delete_preset(self, name: str) -> None:
        presets = self.data.setdefault("presets", {})
        if name in presets:
            del presets[name]
            self.save_settings()

    def save_current_settings(self, settings: dict[str, Any]) -> None:
        self.data["current"] = settings
        self.save_settings()

    def get_current_settings(self) -> dict[str, Any]:
        return self.data.get("current", {})

    def _get_default_advanced_settings(self) -> dict[str, Any]:
        return copy.deepcopy(DEFAULT_SETTINGS["advanced"])

    def _get_optimal_thread_count(self) -> int:
        cpu_count = os.cpu_count() or 4
        return min(max(cpu_count, 2), 8)

    def get_advanced(self, key: str, default: Any = None) -> Any:
        return self.data.setdefault("advanced", {}).get(key, default)

    def set_advanced(self, key: str, value: Any) -> None:
        self.data.setdefault("advanced", {})[key] = value
        self.save_settings()

    def reset_advanced_settings(self) -> None:
        self.data["advanced"] = self._get_default_advanced_settings()
        self.save_settings()
