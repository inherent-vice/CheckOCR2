"""Processing control state for OCR work."""

from __future__ import annotations

import threading


class WorkController:
    def __init__(self) -> None:
        self.is_stopped = False
        self.is_running = False
        self.skip_current = False
        self.current_item = ""
        self.stop_event = threading.Event()

    def start_work(self) -> None:
        self.is_stopped = False
        self.is_running = True
        self.skip_current = False
        self.stop_event.clear()

    def stop_work(self) -> str:
        self.is_stopped = True
        self.is_running = False
        self.stop_event.set()
        return "작업이 중단되었습니다"

    def skip_current_item(self) -> str:
        self.skip_current = True
        return f"현재 항목 '{self.current_item}'을 건너뛰었습니다"

    def reset(self) -> None:
        self.is_stopped = False
        self.is_running = False
        self.skip_current = False
        self.current_item = ""
        self.stop_event.clear()
