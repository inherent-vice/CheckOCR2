from __future__ import annotations

import queue

from checkocr2.exceptions import OCREngineError
from checkocr2.ocr_reader_lifecycle import (
    initialize_easyocr_reader_with_fallback,
    initialize_ocr_reader_with_fallback,
)


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []
        self.criticals = []

    def info(self, message):
        self.infos.append(message)

    def error(self, message):
        self.errors.append(message)

    def critical(self, message):
        self.criticals.append(message)


class FakeSettings:
    def __init__(self, advanced=None):
        self.set_calls = []
        self.advanced = dict(advanced or {})

    def set_advanced(self, key, value):
        self.set_calls.append((key, value))

    def get_advanced(self, key, default=None):
        return self.advanced.get(key, default)


class ReaderFactory:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, languages, *, gpu=False):
        self.calls.append((list(languages), gpu))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_initialize_easyocr_reader_returns_primary_reader():
    reader = object()
    logger = FakeLogger()
    settings = FakeSettings()
    messages = queue.Queue()
    factory = ReaderFactory([reader])

    result = initialize_easyocr_reader_with_fallback(
        logger=logger,
        settings_manager=settings,
        message_queue=messages,
        reader_factory=factory,
    )

    assert result is reader
    assert factory.calls == [(["en"], False)]
    assert settings.set_calls == []
    assert messages.empty()
    assert logger.errors == []
    assert logger.infos[0].startswith("EasyOCR")
    assert "영어 전용" in logger.infos[0]
    assert "['en']" in logger.infos[1]


def test_initialize_easyocr_reader_falls_back_to_cpu_english_mode():
    reader = object()
    logger = FakeLogger()
    settings = FakeSettings()
    messages = queue.Queue()
    factory = ReaderFactory([OCREngineError("primary failed"), reader])

    result = initialize_easyocr_reader_with_fallback(
        logger=logger,
        settings_manager=settings,
        message_queue=messages,
        reader_factory=factory,
    )

    assert result is reader
    assert factory.calls == [(["en"], False), (["en"], False)]
    assert settings.set_calls == [
        ("ocr_gpu_enabled", False),
        ("ocr_languages", ["en"]),
    ]
    assert messages.empty()
    assert "primary failed" in logger.errors[0]
    assert logger.infos[-1]


def test_initialize_easyocr_reader_reports_fatal_failure():
    logger = FakeLogger()
    settings = FakeSettings()
    messages = queue.Queue()
    factory = ReaderFactory(
        [
            OCREngineError("primary failed"),
            RuntimeError("fallback failed"),
        ]
    )

    result = initialize_easyocr_reader_with_fallback(
        logger=logger,
        settings_manager=settings,
        message_queue=messages,
        reader_factory=factory,
    )

    assert result is None
    assert factory.calls == [(["en"], False), (["en"], False)]
    assert settings.set_calls == []
    assert messages.get_nowait()[0] == "error_messagebox"
    assert "fallback failed" in logger.criticals[0]


def test_initialize_ocr_reader_accepts_engine_environment_override(monkeypatch):
    reader = object()
    logger = FakeLogger()
    settings = FakeSettings({"ocr_engine": "easyocr"})
    messages = queue.Queue()
    factory = ReaderFactory([reader])
    monkeypatch.setenv("CHECKOCR2_OCR_ENGINE", "paddle")

    result = initialize_ocr_reader_with_fallback(
        logger=logger,
        settings_manager=settings,
        message_queue=messages,
        reader_factory=factory,
    )

    assert result is reader
    assert factory.calls == [(["ko", "en"], False)]
    assert logger.infos[0].startswith("PaddleOCR")
    assert "언어: ko, en" in logger.infos[0]
    assert "영어 전용" not in logger.infos[0]


def test_initialize_ocr_reader_uses_configured_paddle_engine():
    reader = object()
    logger = FakeLogger()
    settings = FakeSettings({"ocr_engine": "paddle"})
    messages = queue.Queue()
    factory = ReaderFactory([reader])

    result = initialize_ocr_reader_with_fallback(
        logger=logger,
        settings_manager=settings,
        message_queue=messages,
        reader_factory=factory,
    )

    assert result is reader
    assert factory.calls == [(["ko", "en"], False)]
    assert logger.infos[0].startswith("PaddleOCR")
    assert "언어: ko, en" in logger.infos[0]
    assert "영어 전용" not in logger.infos[0]
    assert "['ko', 'en']" in logger.infos[1]
