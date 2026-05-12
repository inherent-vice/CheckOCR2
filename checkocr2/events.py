"""Typed UI event contracts used between workers and Tk UI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class UiEventType(StrEnum):
    LOG = "log"
    LOG_DISPLAY = "log_display"
    ERROR_MESSAGEBOX = "error_messagebox"
    OCR_READY = "ocr_ready"
    GRID_UPDATE = "grid_update"
    STOPPED = "stopped"
    COMPLETE = "complete"
    FINALIZE_EXPORT_AND_COMPLETE = "finalize_export_and_complete"


@dataclass(frozen=True)
class UiEvent:
    type: UiEventType
    payload: tuple[Any, ...] = ()

    def as_legacy_tuple(self) -> tuple[Any, ...]:
        return (self.type.value, *self.payload)


@dataclass(frozen=True)
class LegacyQueueMessage:
    msg_type: str
    payload: tuple[Any, ...] = ()
    known_type: UiEventType | None = None


@dataclass(frozen=True)
class GridUpdate:
    update_type: str
    row_index: int
    payload: tuple[Any, ...] = ()


@dataclass(frozen=True)
class FinalizeExportRequest:
    output_dir: str
    input_path: str
    processed_count: int
    total_items: int


def parse_legacy_grid_update(data: object) -> GridUpdate:
    if not isinstance(data, tuple | list):
        raise TypeError("grid update payload must be a sequence")
    if len(data) < 2:
        raise ValueError("grid update payload requires update type and row index")

    update_type = data[0]
    row_index = data[1]
    if not isinstance(update_type, str):
        raise TypeError("grid update type must be a string")
    if not isinstance(row_index, int):
        raise TypeError("grid update row index must be an integer")
    return GridUpdate(update_type, row_index, tuple(data[2:]))


def parse_legacy_queue_message(message: object) -> LegacyQueueMessage:
    if isinstance(message, UiEvent):
        return LegacyQueueMessage(
            msg_type=message.type.value,
            payload=message.payload,
            known_type=message.type,
        )
    if not isinstance(message, tuple | list):
        raise TypeError("legacy queue message must be a sequence")
    if not message:
        raise ValueError("legacy queue message requires a message type")
    msg_type = message[0]
    if not isinstance(msg_type, str):
        raise TypeError("legacy queue message type must be a string")
    try:
        known_type = UiEventType(msg_type)
    except ValueError:
        known_type = None
    return LegacyQueueMessage(msg_type=msg_type, payload=tuple(message[1:]), known_type=known_type)


def parse_legacy_finalize_export(data: object) -> FinalizeExportRequest:
    if not isinstance(data, tuple | list):
        raise TypeError("finalize export payload must be a sequence")
    if len(data) != 4:
        raise ValueError("finalize export payload requires output, input, processed count, and total items")

    output_dir, input_path, processed_count, total_items = data
    if not isinstance(processed_count, int) or not isinstance(total_items, int):
        raise TypeError("finalize export counts must be integers")

    return FinalizeExportRequest(str(output_dir), str(input_path), processed_count, total_items)


def log_event(message: str, level: str = "INFO") -> UiEvent:
    return UiEvent(UiEventType.LOG, (message, level))


def error_messagebox_event(title: str, message: str) -> UiEvent:
    return UiEvent(UiEventType.ERROR_MESSAGEBOX, (title, message))
