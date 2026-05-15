"""OCR startup loading overlay for the Tk shell."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
from typing import Any

from checkocr2.runtime_state import RuntimeState

LOADING_TITLE = "OCR 모델 준비 중"
LOADING_MESSAGE = "최초 실행 시 모델 캐시 생성으로 시간이 걸릴 수 있습니다."
READY_MESSAGE = "OCR 준비 완료"
ERROR_MESSAGE = "OCR 초기화에 실패했습니다. 로그를 확인하세요."
STAGES = ("앱 시작", "설정 로드", "PaddleOCR 로드", "모델 캐시 확인", "OCR 준비 완료")


class OcrLoadingOverlay:
    def __init__(
        self,
        app: Any,
        *,
        clock: Any = time.monotonic,
        toplevel_factory: Any = tk.Toplevel,
    ):
        self.app = app
        self.clock = clock
        self.started_at = clock()
        self.closed = False
        self.window = toplevel_factory(app)
        self.window.title(LOADING_TITLE)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._close_app)
        try:
            self.window.transient(app)
        except tk.TclError:
            pass

        frame = ttk.Frame(self.window, padding=18)
        frame.pack(fill="both", expand=True)
        self.title_var = tk.StringVar(value=LOADING_TITLE)
        self.message_var = tk.StringVar(value=LOADING_MESSAGE)
        self.elapsed_var = tk.StringVar(value="0.0초")
        self.stage_var = tk.StringVar(value=" > ".join(STAGES[:-1]))

        ttk.Label(frame, textvariable=self.title_var, font=("Segoe UI", 13, "bold")).pack(
            anchor="w"
        )
        ttk.Label(frame, textvariable=self.message_var, wraplength=420).pack(
            anchor="w", pady=(8, 12)
        )
        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=420)
        self.progress.pack(fill="x")
        self.progress.start(12)
        ttk.Label(frame, textvariable=self.stage_var).pack(anchor="w", pady=(12, 0))
        ttk.Label(frame, textvariable=self.elapsed_var).pack(anchor="w", pady=(4, 0))

        self._center()
        self._tick()

    def set_state(self, state: RuntimeState) -> None:
        if self.closed:
            return
        if state is RuntimeState.ERROR:
            self.title_var.set("OCR 준비 실패")
            self.message_var.set(ERROR_MESSAGE)
            self.stage_var.set("오류")
            self.progress.stop()
        elif state is RuntimeState.READY:
            self.title_var.set(READY_MESSAGE)
            self.message_var.set(READY_MESSAGE)
            self.stage_var.set(" > ".join(STAGES))
            self.close()
        elif state is RuntimeState.OCR_LOADING:
            self.title_var.set(LOADING_TITLE)
            self.message_var.set(LOADING_MESSAGE)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.progress.stop()
        except tk.TclError:
            pass
        try:
            self.window.destroy()
        except tk.TclError:
            pass

    def _tick(self) -> None:
        if self.closed:
            return
        self.elapsed_var.set(f"{self.clock() - self.started_at:.1f}초")
        after = getattr(self.window, "after", None)
        if callable(after):
            after(500, self._tick)

    def _center(self) -> None:
        try:
            self.window.update_idletasks()
            app_x = self.app.winfo_rootx()
            app_y = self.app.winfo_rooty()
            app_w = self.app.winfo_width()
            app_h = self.app.winfo_height()
            win_w = self.window.winfo_width()
            win_h = self.window.winfo_height()
            x = app_x + max(0, (app_w - win_w) // 2)
            y = app_y + max(0, (app_h - win_h) // 3)
            self.window.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _close_app(self) -> None:
        quit_app = getattr(self.app, "quit_app", None)
        if callable(quit_app):
            quit_app()
            return
        self.app.destroy()


def update_loading_overlay_for_state(app: Any, state: RuntimeState) -> None:
    if not hasattr(app, "tk"):
        return
    if state is RuntimeState.OCR_LOADING:
        if getattr(app, "ocr_loading_overlay", None) is None:
            try:
                app.ocr_loading_overlay = OcrLoadingOverlay(app)
            except tk.TclError:
                app.ocr_loading_overlay = None
                return
        app.ocr_loading_overlay.set_state(state)
        return

    overlay = getattr(app, "ocr_loading_overlay", None)
    if overlay is None:
        return
    overlay.set_state(state)
    if state is RuntimeState.READY:
        app.ocr_loading_overlay = None
