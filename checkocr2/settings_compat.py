"""Compatibility settings manager for the legacy Tk shell."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from .exceptions import SettingsError
from .settings import DEFAULT_SETTINGS, SettingsStore


class UnifiedSettingsManager(SettingsStore):
    """Compatibility adapter around the package settings store."""

    def __init__(self) -> None:
        try:
            super().__init__()
        except SettingsError as exc:
            print(f"설정 로드 오류: {exc}")
            self.settings_file = "settings.json"
            self.legacy_settings_file = "settings.json"
            self.migration_warning = None
            self.data = copy.deepcopy(DEFAULT_SETTINGS)

    def save_preset(self, name: str, settings: dict[str, Any]) -> None:
        settings = dict(settings)
        settings["created_at"] = datetime.now().isoformat()
        super().save_preset(name, settings)
