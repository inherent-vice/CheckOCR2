"""Preset controller helpers for the legacy Tk GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Any


def update_preset_combo(app: Any) -> None:
    if hasattr(app, "preset_combo") and app.preset_combo:
        preset_names = app.settings_manager.get_preset_names()
        app.preset_combo["values"] = preset_names
        if preset_names:
            app.preset_combo.current(0)
        else:
            app.preset_combo.set("")


def apply_selected_preset(app: Any) -> None:
    if not hasattr(app, "preset_combo"):
        return
    selected = app.preset_combo.get()
    if selected:
        preset_settings = app.settings_manager.apply_preset(selected)
        if preset_settings:
            app.apply_settings_to_ui(preset_settings)
            messagebox.showinfo("정보", f"프리셋 '{selected}'이 적용되었습니다.")
            app.logger.info(f"프리셋 '{selected}' 적용됨.")


def save_current_as_preset(app: Any) -> None:
    name_entry_widget = getattr(app, "preset_name_entry", None)
    name = ""
    if name_entry_widget:
        name = name_entry_widget.get().strip()
        if name == "새 프리셋 이름" or not name:
            messagebox.showwarning("경고", "유효한 프리셋 이름을 입력해주세요.")
            return
    else:
        dialog_name = simpledialog.askstring(
            "프리셋 저장", "프리셋 이름을 입력하세요:", parent=app
        )
        if not dialog_name:
            return
        name = dialog_name

    current_settings = app.get_current_ui_settings()
    app.settings_manager.save_preset(name, current_settings)
    app.update_preset_combo()
    if name_entry_widget:
        name_entry_widget.delete(0, tk.END)
        name_entry_widget.insert(0, "새 프리셋 이름")
    messagebox.showinfo("완료", f"'{name}' 프리셋이 저장되었습니다.")
    app.logger.info(f"프리셋 '{name}' 저장됨.")


def delete_selected_preset(app: Any) -> None:
    if not hasattr(app, "preset_combo"):
        return
    selected = app.preset_combo.get()
    if not selected:
        messagebox.showwarning("경고", "삭제할 프리셋을 선택해주세요.")
        return
    if messagebox.askyesno("확인", f"프리셋 '{selected}'을(를) 삭제하시겠습니까?"):
        app.settings_manager.delete_preset(selected)
        app.update_preset_combo()
        messagebox.showinfo("완료", f"프리셋 '{selected}'이 삭제되었습니다.")
        app.logger.info(f"프리셋 '{selected}' 삭제됨.")
