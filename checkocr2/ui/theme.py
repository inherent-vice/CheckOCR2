"""Tk theme management for the CheckOCR2 GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


class ThemeManager:
    def __init__(self, root_app: Any) -> None:
        self.root_app = root_app
        self.settings_manager = root_app.settings_manager
        self.logger = root_app.logger

        self.available_themes = {
            "modern_blue": {
                "name": "🔵 모던 블루",
                "primary": "#1976D2",
                "secondary": "#42A5F5",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "danger": "#F44336",
                "light": "#F5F5F5",
                "dark": "#212121",
                "white": "#FFFFFF",
                "accent": "#9C27B0",
                "surface": "#FFFFFF",
                "on_surface": "#212121",
                "outline": "#79747E",
                "treeview_bg": "#FFFFFF",
                "treeview_fg": "#000000",
                "treeview_selected_bg": "#AED6F1",
            },
            "dark_pro": {
                "name": "🌙 다크 프로",
                "primary": "#BB86FC",
                "secondary": "#03DAC6",
                "success": "#4CAF50",
                "warning": "#FFC107",
                "danger": "#CF6679",
                "light": "#121212",
                "dark": "#000000",
                "white": "#FFFFFF",
                "accent": "#03DAC6",
                "surface": "#1E1E1E",
                "on_surface": "#E1E1E1",
                "outline": "#938F99",
                "treeview_bg": "#2C2C2C",
                "treeview_fg": "#E1E1E1",
                "treeview_selected_bg": "#555555",
            },
            "elegant_purple": {
                "name": "💜 엘레간트 퍼플",
                "primary": "#6750A4",
                "secondary": "#958DA5",
                "success": "#4CAF50",
                "warning": "#F57C00",
                "danger": "#BA1A1A",
                "light": "#FEF7FF",
                "dark": "#21005D",
                "white": "#FFFFFF",
                "accent": "#D0BCFF",
                "surface": "#FFFBFE",
                "on_surface": "#1D1B20",
                "outline": "#79747E",
                "treeview_bg": "#FFFBFE",
                "treeview_fg": "#1D1B20",
                "treeview_selected_bg": "#E8DEF8",
            },
            "green_nature": {
                "name": "🌿 그린 네이처",
                "primary": "#006E26",
                "secondary": "#52634F",
                "success": "#4CAF50",
                "warning": "#F57C00",
                "danger": "#BA1A1A",
                "light": "#F6FFF6",
                "dark": "#00210A",
                "white": "#FFFFFF",
                "accent": "#006E26",
                "surface": "#FEFFFE",
                "on_surface": "#1A1C18",
                "outline": "#72796F",
                "treeview_bg": "#FEFFFE",
                "treeview_fg": "#1A1C18",
                "treeview_selected_bg": "#C8E6C9",
            },
            "orange_warm": {
                "name": "🧡 오렌지 웜",
                "primary": "#8F4E00",
                "secondary": "#77574B",
                "success": "#4CAF50",
                "warning": "#FF8F00",
                "danger": "#BA1A1A",
                "light": "#FFFBF8",
                "dark": "#2F1500",
                "white": "#FFFFFF",
                "accent": "#FFB59D",
                "surface": "#FFFBF8",
                "on_surface": "#201A16",
                "outline": "#837568",
                "treeview_bg": "#FFFBF8",
                "treeview_fg": "#201A16",
                "treeview_selected_bg": "#FFCCBC",
            },
        }

        saved_theme_key = self.settings_manager.get_advanced("ui_theme", "modern_blue")
        self.current_theme_key = saved_theme_key if saved_theme_key in self.available_themes else "modern_blue"
        self.colors = self.available_themes[self.current_theme_key].copy()
        self.themed_widgets: dict[Any, dict[str, Any]] = {}

    def register_widget(self, widget: Any, style_map: dict[str, Any]) -> None:
        if widget:
            self.themed_widgets[widget] = style_map

    def get_color(self, key: str, default: str | None = None) -> str:
        return self.colors.get(key, default if default is not None else "#000000")

    def apply_theme_to_all_widgets(self) -> None:
        self.root_app.configure(bg=self.get_color("surface"))
        non_color_props = {
            "relief",
            "bd",
            "borderwidth",
            "width",
            "height",
            "padx",
            "pady",
            "state",
            "cursor",
            "font",
            "justify",
            "anchor",
            "wrap",
            "style",
        }

        for widget, style_map in list(self.themed_widgets.items()):
            if not widget or not widget.winfo_exists():
                del self.themed_widgets[widget]
                continue

            config_options = {}
            for tk_prop, value in style_map.items():
                if tk_prop in non_color_props:
                    config_options[tk_prop] = value
                elif isinstance(value, str) and value in self.colors:
                    config_options[tk_prop] = self.colors[value]
                else:
                    config_options[tk_prop] = value

            if config_options:
                try:
                    widget.configure(**config_options)
                except tk.TclError as exc:
                    self.logger.warning(f"위젯 스타일 적용 오류 ({widget}): {exc}")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=self.get_color("treeview_bg"),
            foreground=self.get_color("treeview_fg"),
            fieldbackground=self.get_color("treeview_bg"),
            font=("Segoe UI", 9),
        )
        style.map(
            "Treeview",
            background=[("selected", self.get_color("treeview_selected_bg"))],
            foreground=[("selected", self.get_color("treeview_fg"))],
        )
        style.configure(
            "Treeview.Heading",
            background=self.get_color("primary"),
            foreground=self.get_color("white"),
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Treeview.Heading", background=[("active", self.get_color("secondary"))])
        style.configure(
            "TProgressbar",
            background=self.get_color("success"),
            troughcolor=self.get_color("light"),
            bordercolor=self.get_color("primary"),
            troughrelief="flat",
        )
        style.configure(
            "TScrollbar",
            gripcount=0,
            background=self.get_color("primary"),
            darkcolor=self.get_color("light"),
            lightcolor=self.get_color("light"),
            troughcolor=self.get_color("surface"),
            bordercolor=self.get_color("outline"),
            arrowcolor=self.get_color("white"),
        )
        style.map("TScrollbar", background=[("active", self.get_color("secondary"))])
        style.configure(
            "TCombobox",
            fieldbackground=self.get_color("white"),
            background=self.get_color("secondary"),
            foreground=self.get_color("on_surface"),
            arrowcolor=self.get_color("primary"),
            selectbackground=self.get_color("light"),
            selectforeground=self.get_color("on_surface"),
        )
        style.map("TCombobox", fieldbackground=[("readonly", self.get_color("white"))])

        if hasattr(self.root_app, "log_text_widget") and self.root_app.log_text_widget and self.root_app.log_text_widget.winfo_exists():
            log_widget = self.root_app.log_text_widget
            log_widget.tag_configure("INFO", foreground=self.get_color("primary"))
            log_widget.tag_configure("WARNING", foreground=self.get_color("warning"))
            log_widget.tag_configure("ERROR", foreground=self.get_color("danger"))
            log_widget.tag_configure("SUCCESS", foreground=self.get_color("success"))
            log_widget.tag_configure("DEBUG", foreground=self.get_color("secondary"))

        if hasattr(self.root_app, "refresh_grid_tags"):
            self.root_app.refresh_grid_tags()

    def change_theme(self, theme_key: str) -> None:
        if theme_key in self.available_themes:
            self.current_theme_key = theme_key
            self.colors = self.available_themes[theme_key].copy()
            self.settings_manager.set_advanced("ui_theme", theme_key)
            self.apply_theme_to_all_widgets()
            self.logger.info(f"테마 변경됨: {self.available_themes[theme_key]['name']}")
        else:
            self.logger.warning(f"알 수 없는 테마 키: {theme_key}")
