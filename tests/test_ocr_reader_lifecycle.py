from __future__ import annotations

import queue

from checkocr2.exceptions import OCREngineError
from checkocr2.ocr_reader_lifecycle import initialize_easyocr_reader_with_fallback


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
    def __init__(self):
        self.set_calls = []

    def set_advanced(self, key, value):
        self.set_calls.append((key, value))


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
    assert logger.infos == [
        "EasyOCR 초기화 중... (영어 전용)",
        "EasyOCR 초기화 완료 - 언어: ['en'], GPU: False",
    ]


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
    assert logger.errors == ["EasyOCR 초기화 실패: primary failed"]
    assert logger.infos[-2:] == [
        "기본 모드(영어, CPU)로 EasyOCR 재초기화 시도...",
        "EasyOCR 영어 모드(CPU)로 초기화 완료.",
    ]


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
    assert messages.get_nowait() == (
        "error_messagebox",
        "치명적 오류",
        "OCR 엔진 초기화에 완전히 실패했습니다: fallback failed",
    )
    assert logger.criticals == ["OCR 엔진 초기화 완전 실패: fallback failed"]
