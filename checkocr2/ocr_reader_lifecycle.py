"""EasyOCR reader initialization lifecycle helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from .exceptions import OCREngineError
from .ocr_engine import EasyOcrReaderLike, create_easyocr_reader

OCR_INIT_EXCEPTIONS = (ImportError, OSError, RuntimeError, ValueError, OCREngineError)


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
    languages = ["en"]
    gpu_enabled = False

    try:
        logger.info("EasyOCR 초기화 중... (영어 전용)")
        reader = reader_factory(languages, gpu=gpu_enabled)
        logger.info(f"EasyOCR 초기화 완료 - 언어: {languages}, GPU: {gpu_enabled}")
        return reader
    except OCR_INIT_EXCEPTIONS as exc:
        logger.error(f"EasyOCR 초기화 실패: {exc}")

    try:
        logger.info("기본 모드(영어, CPU)로 EasyOCR 재초기화 시도...")
        reader = reader_factory(["en"], gpu=False)
        settings_manager.set_advanced("ocr_gpu_enabled", False)
        settings_manager.set_advanced("ocr_languages", ["en"])
        logger.info("EasyOCR 영어 모드(CPU)로 초기화 완료.")
        return reader
    except OCR_INIT_EXCEPTIONS as exc:
        message_queue.put(
            ("error_messagebox", "치명적 오류", f"OCR 엔진 초기화에 완전히 실패했습니다: {exc}")
        )
        logger.critical(f"OCR 엔진 초기화 완전 실패: {exc}")
        return None
