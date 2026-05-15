from __future__ import annotations

from checkocr2.ocr_runtime_options import (
    minimum_confidence,
    normalize_rate_decimal_places,
    ocr_detail_level,
    rate_decimal_places,
)


class FakeSettings:
    def __init__(self, values=None):
        self.values = values or {}
        self.calls = []

    def get_advanced(self, key, default=None):
        self.calls.append((key, default))
        return self.values.get(key, default)


def test_ocr_detail_level_accepts_only_legacy_detail_one():
    assert ocr_detail_level(FakeSettings({"ocr_detail_level": 1})) == 1
    assert ocr_detail_level(FakeSettings({"ocr_detail_level": "1"})) == 1
    assert ocr_detail_level(FakeSettings({"ocr_detail_level": 0})) == 0
    assert ocr_detail_level(FakeSettings({"ocr_detail_level": 2})) == 0
    assert ocr_detail_level(FakeSettings({"ocr_detail_level": "bad"})) == 0
    assert ocr_detail_level(FakeSettings({"ocr_detail_level": None})) == 0


def test_ocr_detail_level_uses_default_zero():
    settings = FakeSettings()

    assert ocr_detail_level(settings) == 0
    assert settings.calls == [("ocr_detail_level", 0)]


def test_minimum_confidence_uses_field_specific_setting_key():
    settings = FakeSettings({"min_date_confidence": "80"})

    assert minimum_confidence(settings, "date") == "80"
    assert minimum_confidence(settings, "rate") == 0.0
    assert settings.calls == [
        ("min_date_confidence", 0.0),
        ("min_rate_confidence", 0.0),
    ]


def test_rate_decimal_places_uses_default_and_clamps_invalid_values():
    assert rate_decimal_places(FakeSettings()) == 4
    assert rate_decimal_places(FakeSettings({"rate_decimal_places": "4"})) == 4
    assert rate_decimal_places(FakeSettings({"rate_decimal_places": 0})) == 1
    assert rate_decimal_places(FakeSettings({"rate_decimal_places": 99})) == 6
    assert rate_decimal_places(FakeSettings({"rate_decimal_places": "bad"})) == 4


def test_normalize_rate_decimal_places_clamps_to_supported_range():
    assert normalize_rate_decimal_places(None) == 4
    assert normalize_rate_decimal_places(2) == 2
    assert normalize_rate_decimal_places(0) == 1
    assert normalize_rate_decimal_places(12) == 6
