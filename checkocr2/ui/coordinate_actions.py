"""Coordinate capture and preview actions for the legacy Tk shell."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from checkocr2.ui.overlays import AreaVisualizationOverlay, DragCaptureOverlay, PointCaptureOverlay


def relocate_clickpoint(
    app: Any,
    *,
    point_overlay_factory: Callable[..., Any] = PointCaptureOverlay,
) -> None:
    overlay = point_overlay_factory(app, color_key="danger", theme_manager=app.theme_manager)
    app.wait_window(overlay)
    if overlay.click_x is not None:
        app.click_x.set(overlay.click_x)
        app.click_y.set(overlay.click_y)


def relocate_area(
    app: Any,
    x1_var: Any,
    y1_var: Any,
    x2_var: Any,
    y2_var: Any,
    color_key: str,
    *,
    drag_overlay_factory: Callable[..., Any] = DragCaptureOverlay,
) -> None:
    overlay = drag_overlay_factory(app, color_key=color_key, theme_manager=app.theme_manager)
    app.wait_window(overlay)
    if overlay.x1 is not None:
        x1_var.set(overlay.x1)
        y1_var.set(overlay.y1)
        x2_var.set(overlay.x2)
        y2_var.set(overlay.y2)


def current_areas_info(app: Any) -> dict[str, tuple[int, ...]]:
    return {
        "click_point": (app.click_x.get(), app.click_y.get()),
        "all_area": (
            app.allarea_x1.get(),
            app.allarea_y1.get(),
            app.allarea_x2.get(),
            app.allarea_y2.get(),
        ),
        "date_area": (
            app.datearea_x1.get(),
            app.datearea_y1.get(),
            app.datearea_x2.get(),
            app.datearea_y2.get(),
        ),
        "rate_area": (
            app.ratearea_x1.get(),
            app.ratearea_y1.get(),
            app.ratearea_x2.get(),
            app.ratearea_y2.get(),
        ),
    }


def show_area_preview(
    app: Any,
    *,
    preview_overlay_factory: Callable[..., Any] = AreaVisualizationOverlay,
) -> None:
    preview_overlay_factory(
        app,
        current_areas_info(app),
        app.theme_manager,
        auto_close=True,
    )
