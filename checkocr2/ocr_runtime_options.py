"""OCR runtime option helpers."""

from __future__ import annotations

from typing import Any, Protocol


class AdvancedSettingsLike(Protocol):
    def get_advanced(self, key: str, default: Any = None) -> Any: ...


def ocr_detail_level(settings_manager: AdvancedSettingsLike) -> int:
    try:
        return 1 if int(settings_manager.get_advanced("ocr_detail_level", 0)) == 1 else 0
    except (TypeError, ValueError):
        return 0


def minimum_confidence(settings_manager: AdvancedSettingsLike, field_key: str) -> Any:
    return settings_manager.get_advanced(f"min_{field_key}_confidence", 0.0)
