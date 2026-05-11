"""Settings-to-Tk-variable binding helpers for the legacy GUI."""

from __future__ import annotations

from typing import Any

from checkocr2.exceptions import SettingsError


def collect_ui_settings(app: Any) -> dict[str, Any]:
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
        "delays": {
            "paste": app.paste_delay.get(),
            "loading": app.loading_delay.get(),
        },
        "save_detail_images": app.save_detail_images.get(),
        "skip_kbp_code": app.skip_kbp_var.get(),
        "upscaling": {
            "enabled": app.enable_upscaling.get(),
            "factor": app.upscaling_factor.get(),
            "method": app.upscaling_method.get(),
        },
    }


def build_current_settings(app: Any) -> dict[str, Any]:
    current_settings = collect_ui_settings(app)
    current_settings["input_excel_path"] = app.input_excel_path.get()
    current_settings["output_folder_path"] = app.output_folder_path.get()
    return current_settings


def apply_ui_settings(app: Any, settings_dict: dict[str, Any] | None) -> None:
    if not settings_dict:
        return

    click_point = settings_dict.get("click_point", (0, 0))
    app.click_x.set(click_point[0])
    app.click_y.set(click_point[1])

    areas = {
        "all_area": (app.allarea_x1, app.allarea_y1, app.allarea_x2, app.allarea_y2),
        "date_area": (app.datearea_x1, app.datearea_y1, app.datearea_x2, app.datearea_y2),
        "rate_area": (app.ratearea_x1, app.ratearea_y1, app.ratearea_x2, app.ratearea_y2),
    }
    for key, tk_vars in areas.items():
        coords = settings_dict.get(key)
        if coords and len(coords) == 4:
            tk_vars[0].set(coords[0])
            tk_vars[1].set(coords[1])
            tk_vars[2].set(coords[2])
            tk_vars[3].set(coords[3])

    delays = settings_dict.get("delays", {})
    app.paste_delay.set(delays.get("paste", 0.5))
    app.loading_delay.set(delays.get("loading", 2.5))
    app.save_detail_images.set(settings_dict.get("save_detail_images", True))
    app.skip_kbp_var.set(settings_dict.get("skip_kbp_code", True))

    upscaling_settings = settings_dict.get("upscaling", {})
    app.enable_upscaling.set(upscaling_settings.get("enabled", True))
    app.upscaling_factor.set(upscaling_settings.get("factor", 2.0))
    app.upscaling_method.set(upscaling_settings.get("method", "LANCZOS"))

    if "advanced" in settings_dict:
        app.settings_manager.data["advanced"].update(settings_dict["advanced"])


def save_advanced_settings(app: Any) -> None:
    try:
        app.settings_manager.set_advanced("skip_kbp_code", app.skip_kbp_var.get())
        app.settings_manager.set_advanced("upscaling_enabled", app.enable_upscaling.get())
        app.settings_manager.set_advanced("upscaling_factor", app.upscaling_factor.get())
        app.settings_manager.set_advanced("upscaling_method", app.upscaling_method.get())
        app.settings_manager.save_settings()
        app.logger.info("고급 설정이 저장되었습니다.")
    except (OSError, SettingsError, TypeError, ValueError) as exc:
        app.logger.error(f"고급 설정 저장 실패: {exc}")
