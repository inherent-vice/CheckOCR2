"""Processing control state for OCR work."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkStateSnapshot:
    is_stopped: bool
    is_running: bool
    skip_current: bool
    current_item: str
    stop_event_is_set: bool


class WorkController:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.is_stopped = False
        self.is_running = False
        self.skip_current = False
        self.current_item = ""
        self.stop_event = threading.Event()

    def start_work(self) -> None:
        with self._lock:
            self.is_stopped = False
            self.is_running = True
            self.skip_current = False
            self.stop_event.clear()

    def stop_work(self) -> str:
        with self._lock:
            self.is_stopped = True
            self.is_running = False
            self.stop_event.set()
        return "작업이 중단되었습니다"

    def skip_current_item(self) -> str:
        with self._lock:
            self.skip_current = True
            current_item = self.current_item
        return f"현재 항목 '{current_item}'을 건너뛰었습니다"

    def reset(self) -> None:
        with self._lock:
            self.is_stopped = False
            self.is_running = False
            self.skip_current = False
            self.current_item = ""
            self.stop_event.clear()

    def set_current_item(self, value: str) -> None:
        with self._lock:
            self.current_item = value

    def set_skip_current(self, value: bool) -> None:
        with self._lock:
            self.skip_current = value

    def snapshot(self) -> WorkStateSnapshot:
        with self._lock:
            return WorkStateSnapshot(
                is_stopped=self.is_stopped,
                is_running=self.is_running,
                skip_current=self.skip_current,
                current_item=self.current_item,
                stop_event_is_set=self.stop_event.is_set(),
            )
