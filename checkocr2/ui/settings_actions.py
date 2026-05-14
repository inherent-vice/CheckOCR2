"""Settings load/save action helpers for the legacy Tk shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox
from typing import Any

from checkocr2.exceptions import SettingsError
from checkocr2.ui.settings_binding import build_current_settings


def load_last_settings(app: Any) -> None:
    try:
        settings = app.settings_manager.get_current_settings()
        if settings:
            app.apply_settings_to_ui(settings)
            app.input_excel_path.set(settings.get("input_excel_path", ""))
            app.output_folder_path.set(settings.get("output_folder_path", ""))
            app.logger.info("마지막 설정이 성공적으로 불러와졌습니다.")
        else:
            app.logger.info("저장된 현재 설정이 없습니다. 기본값을 사용합니다.")
            app.settings_manager.data["advanced"] = (
                app.settings_manager._get_default_advanced_settings()
            )
        app.update_preset_combo()
        app.theme_manager.change_theme(
            app.settings_manager.get_advanced("ui_theme", "modern_blue")
        )
    except (OSError, SettingsError, tk.TclError, TypeError, ValueError) as exc:
        app.logger.error(f"설정 불러오기 실패: {exc}")


def quick_save_settings(
    app: Any,
    *,
    show_error: Callable[[str, str], object] | None = None,
) -> None:
    """Save the current UI settings through the legacy settings manager."""
    try:
        current_settings = build_current_settings(app)
        app.settings_manager.save_current_settings(current_settings)
        app.save_advanced_ui_to_settings()
        app.logger.info("현재 설정이 저장되었습니다.")
    except (OSError, SettingsError, tk.TclError, TypeError, ValueError) as exc:
        app.logger.error(f"설정 저장 실패: {exc}")
        if show_error is None:
            show_error = messagebox.showerror
        show_error("오류", f"설정 저장 중 오류가 발생했습니다: {exc}")


def reset_advanced_settings_and_ui(
    app: Any,
    *,
    ask_confirm: Callable[[str, str], bool] | None = None,
    show_info: Callable[[str, str], object] | None = None,
) -> None:
    if ask_confirm is None:
        ask_confirm = messagebox.askyesno
    if show_info is None:
        show_info = messagebox.showinfo

    if ask_confirm("확인", "모든 고급 설정을 기본값으로 되돌리시겠습니까?"):
        app.settings_manager.reset_advanced_settings()
        app.skip_kbp_var.set(app.settings_manager.get_advanced("skip_kbp_code", True))
        app.rate_decimal_places.set(app.settings_manager.get_advanced("rate_decimal_places", 3))
        show_info("완료", "고급 설정이 초기화되었습니다.")
        app.logger.info("고급 설정이 기본값으로 초기화되었습니다.")
