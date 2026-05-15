"""OCR runtime option helpers."""

from __future__ import annotations

from typing import Any, Protocol

DEFAULT_RATE_DECIMAL_PLACES = 4
MIN_RATE_DECIMAL_PLACES = 1
MAX_RATE_DECIMAL_PLACES = 6


class AdvancedSettingsLike(Protocol):
    def get_advanced(self, key: str, default: Any = None) -> Any: ...


def ocr_detail_level(settings_manager: AdvancedSettingsLike) -> int:
    try:
        return 1 if int(settings_manager.get_advanced("ocr_detail_level", 0)) == 1 else 0
    except (TypeError, ValueError):
        return 0


def minimum_confidence(settings_manager: AdvancedSettingsLike, field_key: str) -> Any:
    return settings_manager.get_advanced(f"min_{field_key}_confidence", 0.0)


def normalize_rate_decimal_places(value: Any) -> int:
    try:
        precision = int(value)
    except (TypeError, ValueError):
        return DEFAULT_RATE_DECIMAL_PLACES
    return max(MIN_RATE_DECIMAL_PLACES, min(MAX_RATE_DECIMAL_PLACES, precision))


def rate_decimal_places(settings_manager: AdvancedSettingsLike) -> int:
    return normalize_rate_decimal_places(
        settings_manager.get_advanced("rate_decimal_places", DEFAULT_RATE_DECIMAL_PLACES)
    )
