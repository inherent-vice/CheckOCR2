"""Main window layout assembly for the legacy Tk shell."""

from __future__ import annotations

import tkinter as tk
from logging import Logger
from queue import Queue
from typing import Protocol

from checkocr2.logging_config import TkinterLogHandler
from checkocr2.ui.menu import create_menu
from checkocr2.ui.panels.coordinates_panel import create_coordinates_panel
from checkocr2.ui.panels.file_panel import create_file_panel
from checkocr2.ui.panels.grid_panel import create_grid_panel
from checkocr2.ui.panels.log_panel import create_log_panel
from checkocr2.ui.panels.options_panel import create_options_panel
from checkocr2.ui.panels.preset_panel import create_preset_panel
from checkocr2.ui.panels.timing_panel import create_timing_panel
from checkocr2.ui.toolbar import create_simple_toolbar


class ThemeManagerLike(Protocol):
    def get_color(self, color_key: str, default: str | None = None) -> str: ...

    def register_widget(
        self, widget: object, style_config: dict[str, object]
    ) -> None: ...


class MainWindowHost(Protocol):
    theme_manager: ThemeManagerLike
    message_queue: Queue
    logger: Logger
    log_text_widget: object | None

    def configure(self, **kwargs: object) -> None: ...

    def grid_rowconfigure(self, index: int, **kwargs: object) -> None: ...

    def grid_columnconfigure(self, index: int, **kwargs: object) -> None: ...

    def _create_menu(self) -> None: ...

    def _create_simple_toolbar(self) -> None: ...

    def _create_left_panel_content(self, parent: object) -> None: ...

    def _create_center_excel_grid(self, parent: object) -> None: ...

    def _create_right_panel_content(self, parent: object) -> None: ...

    def _create_file_section(self, parent: object) -> None: ...

    def _create_coordinates_section(self, parent: object) -> None: ...

    def _create_timing_section(self, parent: object) -> None: ...

    def _create_options_section(self, parent: object) -> None: ...

    def _create_preset_section(self, parent: object) -> None: ...


def build_main_window(app: MainWindowHost) -> None:
    app.configure(bg=app.theme_manager.get_color("surface"))
    app._create_menu()
    app._create_simple_toolbar()

    app.grid_rowconfigure(0, weight=0)
    app.grid_rowconfigure(1, weight=1)
    app.grid_columnconfigure(0, weight=1)

    main_container = tk.Frame(app)
    app.theme_manager.register_widget(main_container, {"bg": "surface"})
    main_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

    main_container.grid_rowconfigure(0, weight=1)
    main_container.grid_columnconfigure(0, weight=0, minsize=280)
    main_container.grid_columnconfigure(1, weight=6)
    main_container.grid_columnconfigure(2, weight=1, minsize=200)

    left_panel = tk.Frame(main_container)
    app.theme_manager.register_widget(left_panel, {"bg": "surface"})
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=5)

    center_panel = tk.Frame(main_container)
    app.theme_manager.register_widget(center_panel, {"bg": "surface"})
    center_panel.grid(row=0, column=1, sticky="nsew", padx=3, pady=5)

    right_panel = tk.Frame(main_container)
    app.theme_manager.register_widget(right_panel, {"bg": "surface"})
    right_panel.grid(row=0, column=2, sticky="nsew", padx=(2, 5), pady=5)

    app._create_left_panel_content(left_panel)
    app._create_center_excel_grid(center_panel)
    app._create_right_panel_content(right_panel)

    if app.log_text_widget:
        tkinter_handler = TkinterLogHandler(app.log_text_widget, app.message_queue)
        app.logger.addHandler(tkinter_handler)


def create_menu_bar(app: object) -> None:
    create_menu(app)


def create_toolbar(app: object) -> None:
    create_simple_toolbar(app)


def create_left_panel_content(app: MainWindowHost, parent: object) -> None:
    scrollable_frame = tk.Frame(parent)
    app.theme_manager.register_widget(scrollable_frame, {"bg": "surface"})
    scrollable_frame.pack(fill="both", expand=True, padx=0, pady=0)

    app._create_file_section(scrollable_frame)
    app._create_coordinates_section(scrollable_frame)
    app._create_timing_section(scrollable_frame)
    app._create_options_section(scrollable_frame)
    app._create_preset_section(scrollable_frame)


def create_right_panel_content(app: MainWindowHost, parent: object) -> None:
    app.log_text_widget = create_log_panel(app, parent)


def create_file_section(app: object, parent: object) -> None:
    create_file_panel(app, parent)


def create_coordinates_section(app: object, parent: object) -> None:
    create_coordinates_panel(app, parent)


def create_timing_section(app: object, parent: object) -> None:
    create_timing_panel(app, parent)


def create_options_section(app: object, parent: object) -> None:
    create_options_panel(app, parent)


def create_preset_section(app: object, parent: object) -> None:
    create_preset_panel(app, parent)


def create_center_excel_grid(app: object, parent: object) -> None:
    create_grid_panel(app, parent)
