"""EasyOCR reader initialization lifecycle helpers."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, Protocol

from .exceptions import OCREngineError
from .ocr_engine import (
    OCR_ENGINE_EASYOCR,
    OCR_ENGINE_PADDLE,
    BlankFallbackOcrReader,
    EasyOcrReaderLike,
    create_easyocr_reader,
    create_ocr_reader,
    default_ocr_languages,
    normalize_ocr_engine,
)

OCR_INIT_EXCEPTIONS = (ImportError, OSError, RuntimeError, ValueError, OCREngineError)
OCR_ENGINE_ENV = "CHECKOCR2_OCR_ENGINE"


class LoggerLike(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def critical(self, message: str) -> None: ...


class MessageQueueLike(Protocol):
    def put(self, item: tuple[str, str, str]) -> None: ...


class SettingsManagerLike(Protocol):
    def set_advanced(self, key: str, value: Any) -> None: ...


class ReaderFactory(Protocol):
    def __call__(self, languages: Sequence[str], *, gpu: bool = False) -> EasyOcrReaderLike: ...


def initialize_easyocr_reader_with_fallback(
    *,
    logger: LoggerLike,
    settings_manager: SettingsManagerLike,
    message_queue: MessageQueueLike,
    reader_factory: ReaderFactory = create_easyocr_reader,
) -> EasyOcrReaderLike | None:
    return initialize_ocr_reader_with_fallback(
        logger=logger,
        settings_manager=settings_manager,
        message_queue=message_queue,
        reader_factory=reader_factory,
        engine_name=OCR_ENGINE_EASYOCR,
    )


def initialize_ocr_reader_with_fallback(
    *,
    logger: LoggerLike,
    settings_manager: SettingsManagerLike,
    message_queue: MessageQueueLike,
    reader_factory: ReaderFactory | None = None,
    engine_name: str | None = None,
) -> EasyOcrReaderLike | None:
    gpu_enabled = False
    selected_engine = normalize_ocr_engine(
        engine_name or configured_ocr_engine(settings_manager)
    )
    languages = default_ocr_languages(selected_engine)
    primary_label = engine_label(selected_engine)
    using_default_factory = reader_factory is None

    if reader_factory is None:
        def reader_factory(langs, *, gpu=False):
            return create_ocr_reader(
                selected_engine,
                langs,
                gpu=gpu,
            )

    try:
        logger.info(f"{primary_label} 초기화 중... ({language_label(languages)})")
        reader = reader_factory(languages, gpu=gpu_enabled)
        if selected_engine == OCR_ENGINE_PADDLE and using_default_factory:
            reader = add_easyocr_blank_fallback(reader, logger=logger)
        logger.info(
            f"{primary_label} 초기화 완료 - 언어: {languages}, GPU: {gpu_enabled}"
        )
        return reader
    except OCR_INIT_EXCEPTIONS as exc:
        logger.error(f"{primary_label} 초기화 실패: {exc}")

    try:
        logger.info("기본 모드(영어, CPU)로 EasyOCR 재초기화 시도...")
        reader = fallback_easyocr_reader(
            selected_engine=selected_engine,
            reader_factory=reader_factory,
        )
        settings_manager.set_advanced("ocr_gpu_enabled", False)
        settings_manager.set_advanced("ocr_languages", ["en"])
        if selected_engine != OCR_ENGINE_EASYOCR:
            settings_manager.set_advanced("ocr_engine", OCR_ENGINE_EASYOCR)
        logger.info("EasyOCR 영어 모드(CPU)로 초기화 완료.")
        return reader
    except OCR_INIT_EXCEPTIONS as exc:
        message_queue.put(
            ("error_messagebox", "치명적 오류", f"OCR 엔진 초기화에 완전히 실패했습니다: {exc}")
        )
        logger.critical(f"OCR 엔진 초기화 완전 실패: {exc}")
        return None


def configured_ocr_engine(settings_manager: SettingsManagerLike) -> str:
    env_value = os.environ.get(OCR_ENGINE_ENV)
    if env_value:
        return env_value
    get_advanced = getattr(settings_manager, "get_advanced", None)
    if callable(get_advanced):
        return str(get_advanced("ocr_engine", OCR_ENGINE_EASYOCR))
    return OCR_ENGINE_EASYOCR


def engine_label(engine_name: str) -> str:
    if engine_name == OCR_ENGINE_PADDLE:
        return "PaddleOCR"
    return "EasyOCR"


def language_label(languages: Sequence[str]) -> str:
    if list(languages) == ["en"]:
        return "영어 전용"
    return "언어: " + ", ".join(languages)


def fallback_easyocr_reader(
    *,
    selected_engine: str,
    reader_factory: ReaderFactory,
) -> EasyOcrReaderLike:
    if selected_engine == OCR_ENGINE_EASYOCR:
        return reader_factory(["en"], gpu=False)
    return create_ocr_reader(OCR_ENGINE_EASYOCR, ["en"], gpu=False)


def add_easyocr_blank_fallback(
    reader: EasyOcrReaderLike,
    *,
    logger: LoggerLike,
) -> EasyOcrReaderLike:
    try:
        fallback_reader = create_ocr_reader(OCR_ENGINE_EASYOCR, ["en"], gpu=False)
    except OCR_INIT_EXCEPTIONS as exc:
        logger.error(f"PaddleOCR blank fallback unavailable: {exc}")
        return reader
    logger.info("PaddleOCR blank fallback enabled: EasyOCR English CPU")
    return BlankFallbackOcrReader(reader, fallback_reader)
