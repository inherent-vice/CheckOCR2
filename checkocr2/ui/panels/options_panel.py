"""OCR options panel construction for the CheckOCR2 Tk shell."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Protocol


class ThemeManagerLike(Protocol):
    def register_widget(self, widget: object, style_config: dict[str, object]) -> None:
        ...


class SettingsManagerLike(Protocol):
    def get_advanced(self, key: str, default: object = None) -> object:
        ...


class OptionsPanelHost(Protocol):
    theme_manager: ThemeManagerLike
    settings_manager: SettingsManagerLike
    save_detail_images: object
    skip_kbp_var: object
    enable_upscaling: object
    upscaling_factor: object
    upscaling_method: object
    enable_upscaling_cb: object
    upscaling_details_frame: object
    factor_combo: object
    method_combo: object

    def _create_section_frame_styled(
        self,
        parent: object,
        title: str,
        fill_parent: bool = False,
    ) -> object:
        ...

    def save_advanced_ui_to_settings(self) -> None:
        ...

    def on_upscaling_toggle(self) -> None:
        ...


CHECKBOX_STYLE = {
    "bg": "white",
    "fg": "on_surface",
    "selectcolor": "light",
    "activebackground": "white",
    "activeforeground": "on_surface",
}


def create_options_panel(app: OptionsPanelHost, parent: object) -> None:
    section = app._create_section_frame_styled(parent, "⚙️ 옵션 설정")
    common_font = ("Segoe UI", 9)

    save_img_cb = tk.Checkbutton(
        section,
        text="상세 이미지 저장 (영역별 개별 파일)",
        variable=app.save_detail_images,
        font=common_font,
    )
    app.theme_manager.register_widget(save_img_cb, CHECKBOX_STYLE)
    save_img_cb.pack(anchor="w", pady=(0, 8))

    app.skip_kbp_var = tk.BooleanVar(value=app.settings_manager.get_advanced("skip_kbp_code", True))
    skip_kbp_cb = tk.Checkbutton(
        section,
        text="'KBP' 코드 건너뛰기 (빈 값으로 완료 처리)",
        variable=app.skip_kbp_var,
        font=common_font,
        command=app.save_advanced_ui_to_settings,
    )
    app.theme_manager.register_widget(skip_kbp_cb, CHECKBOX_STYLE)
    skip_kbp_cb.pack(anchor="w", pady=(0, 8))

    app.enable_upscaling.set(app.settings_manager.get_advanced("upscaling_enabled", True))
    app.upscaling_factor.set(app.settings_manager.get_advanced("upscaling_factor", 2.0))
    app.upscaling_method.set(app.settings_manager.get_advanced("upscaling_method", "LANCZOS"))

    upscaling_frame = tk.Frame(section)
    app.theme_manager.register_widget(upscaling_frame, {"bg": "white"})
    upscaling_frame.pack(fill="x", pady=(8, 0))

    app.enable_upscaling_cb = tk.Checkbutton(
        upscaling_frame,
        text="🔍 OCR 업스케일링 활성화 (인식률 향상)",
        variable=app.enable_upscaling,
        font=common_font,
        command=app.on_upscaling_toggle,
    )
    app.theme_manager.register_widget(app.enable_upscaling_cb, CHECKBOX_STYLE)
    app.enable_upscaling_cb.pack(anchor="w", pady=(0, 5))

    app.upscaling_details_frame = tk.Frame(upscaling_frame)
    app.theme_manager.register_widget(app.upscaling_details_frame, {"bg": "white"})
    app.upscaling_details_frame.pack(fill="x", padx=(20, 0))

    factor_frame = tk.Frame(app.upscaling_details_frame)
    app.theme_manager.register_widget(factor_frame, {"bg": "white"})
    factor_frame.pack(fill="x", pady=(0, 5))

    factor_lbl = tk.Label(factor_frame, text="배율:", font=common_font, width=8)
    app.theme_manager.register_widget(factor_lbl, {"bg": "white", "fg": "on_surface"})
    factor_lbl.pack(side="left")

    app.factor_combo = ttk.Combobox(
        factor_frame,
        textvariable=app.upscaling_factor,
        values=[1.5, 2.0, 2.5, 3.0, 4.0],
        width=8,
        state="readonly",
        font=common_font,
        style="TCombobox",
    )
    app.factor_combo.pack(side="left", padx=(5, 10))

    factor_desc = tk.Label(
        factor_frame,
        text="(2.0x 권장)",
        font=(common_font[0], common_font[1] - 1),
        foreground="gray",
    )
    app.theme_manager.register_widget(factor_desc, {"bg": "white", "fg": "outline"})
    factor_desc.pack(side="left")

    method_frame = tk.Frame(app.upscaling_details_frame)
    app.theme_manager.register_widget(method_frame, {"bg": "white"})
    method_frame.pack(fill="x")

    method_lbl = tk.Label(method_frame, text="품질:", font=common_font, width=8)
    app.theme_manager.register_widget(method_lbl, {"bg": "white", "fg": "on_surface"})
    method_lbl.pack(side="left")

    app.method_combo = ttk.Combobox(
        method_frame,
        textvariable=app.upscaling_method,
        values=["LANCZOS", "BICUBIC", "BILINEAR"],
        width=10,
        state="readonly",
        font=common_font,
        style="TCombobox",
    )
    app.method_combo.pack(side="left", padx=(5, 10))

    method_desc = tk.Label(
        method_frame,
        text="(LANCZOS 최고품질)",
        font=(common_font[0], common_font[1] - 1),
        foreground="gray",
    )
    app.theme_manager.register_widget(method_desc, {"bg": "white", "fg": "outline"})
    method_desc.pack(side="left")

    app.on_upscaling_toggle()
