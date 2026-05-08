"""Typed UI event contracts used between workers and Tk UI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class UiEventType(StrEnum):
    LOG = "log"
    LOG_DISPLAY = "log_display"
    ERROR_MESSAGEBOX = "error_messagebox"
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


def log_event(message: str, level: str = "INFO") -> UiEvent:
    return UiEvent(UiEventType.LOG, (message, level))


def error_messagebox_event(title: str, message: str) -> UiEvent:
    return UiEvent(UiEventType.ERROR_MESSAGEBOX, (title, message))
