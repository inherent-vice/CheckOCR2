"""Screen capture automation for OCR row processing."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from checkocr2.paths import sanitize_filename
from checkocr2.screen_automation import click, copy_text, hotkey, screenshot


@dataclass(frozen=True)
class CaptureScreenshotsResult:
    date_image: Any | None
    rate_image: Any | None
    timing_ms: dict[str, float]


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


def capture_screenshots(
    stock_code: str,
    save_folder: str | os.PathLike[str],
    coords: dict[str, tuple[int, int, int, int] | tuple[int, int]],
    paste_d: float,
    load_d: float,
    save_details: bool,
    *,
    work_controller: Any,
    settings_manager: Any,
    message_queue: Any,
    copy_text_func: Callable[[str], object] = copy_text,
    click_func: Callable[..., object] = click,
    hotkey_func: Callable[..., object] = hotkey,
    screenshot_func: Callable[..., Any] = screenshot,
) -> CaptureScreenshotsResult:
    capture_started = perf_counter()
    timing: dict[str, float] = {}
    if work_controller.is_stopped:
        timing["capture_total_ms"] = _elapsed_ms(capture_started)
        return CaptureScreenshotsResult(None, None, timing)

    copy_started = perf_counter()
    copy_text_func(stock_code)
    timing["copy_ms"] = _elapsed_ms(copy_started)

    click_x, click_y = coords["click"]
    click_started = perf_counter()
    click_func(
        click_x,
        click_y,
        clicks=2,
        interval=settings_manager.get_advanced("click_interval", 0.1),
    )
    timing["click_ms"] = _elapsed_ms(click_started)

    wait_started = perf_counter()
    if work_controller.stop_event.wait(timeout=paste_d):
        timing["paste_wait_ms"] = _elapsed_ms(wait_started)
        timing["capture_total_ms"] = _elapsed_ms(capture_started)
        return CaptureScreenshotsResult(None, None, timing)

    timing["paste_wait_ms"] = _elapsed_ms(wait_started)
    paste_started = perf_counter()
    hotkey_func("ctrl", "v")
    timing["paste_hotkey_ms"] = _elapsed_ms(paste_started)

    wait_started = perf_counter()
    if work_controller.stop_event.wait(timeout=load_d):
        timing["load_wait_ms"] = _elapsed_ms(wait_started)
        timing["capture_total_ms"] = _elapsed_ms(capture_started)
        return CaptureScreenshotsResult(None, None, timing)
    timing["load_wait_ms"] = _elapsed_ms(wait_started)

    safe_stock_code = sanitize_filename(stock_code)
    date_img_src, rate_img_src = None, None

    x1_all, y1_all, x2_all, y2_all = coords["all"]
    if not (x2_all > x1_all and y2_all > y1_all):
        message_queue.put(("log", f"[{safe_stock_code}] 전체 영역 좌표 오류: {coords['all']}", "ERROR"))
        timing["capture_total_ms"] = _elapsed_ms(capture_started)
        return CaptureScreenshotsResult(None, None, timing)

    if save_details:
        screenshot_started = perf_counter()
        screenshot_all = screenshot_func(region=(x1_all, y1_all, x2_all - x1_all, y2_all - y1_all))
        timing["capture_all_ms"] = _elapsed_ms(screenshot_started)
        save_started = perf_counter()
        allarea_path = os.path.join(save_folder, f"{safe_stock_code}.png")
        screenshot_all.save(allarea_path)
        timing["save_all_ms"] = _elapsed_ms(save_started)
        message_queue.put(("log", f"전체 영역 이미지 저장: {allarea_path}", "INFO"))
    else:
        timing["capture_all_ms"] = 0.0
        timing["save_all_ms"] = 0.0

    x1_date, y1_date, x2_date, y2_date = coords["date"]
    if not (x2_date > x1_date and y2_date > y1_date):
        message_queue.put(("log", f"[{safe_stock_code}] 날짜 영역 좌표 오류: {coords['date']}", "ERROR"))
    else:
        screenshot_started = perf_counter()
        screenshot_date = screenshot_func(region=(x1_date, y1_date, x2_date - x1_date, y2_date - y1_date))
        timing["capture_date_ms"] = _elapsed_ms(screenshot_started)
        if save_details:
            save_started = perf_counter()
            date_img_src = os.path.join(save_folder, f"{safe_stock_code}_date.png")
            screenshot_date.save(date_img_src)
            timing["save_date_ms"] = _elapsed_ms(save_started)
            message_queue.put(("log", f"날짜 영역 이미지 저장: {date_img_src}", "INFO"))
        else:
            timing["save_date_ms"] = 0.0
            date_img_src = screenshot_date

    x1_rate, y1_rate, x2_rate, y2_rate = coords["rate"]
    if not (x2_rate > x1_rate and y2_rate > y1_rate):
        message_queue.put(("log", f"[{safe_stock_code}] 금리 영역 좌표 오류: {coords['rate']}", "ERROR"))
    else:
        screenshot_started = perf_counter()
        screenshot_rate = screenshot_func(region=(x1_rate, y1_rate, x2_rate - x1_rate, y2_rate - y1_rate))
        timing["capture_rate_ms"] = _elapsed_ms(screenshot_started)
        if save_details:
            save_started = perf_counter()
            rate_img_src = os.path.join(save_folder, f"{safe_stock_code}_rate.png")
            screenshot_rate.save(rate_img_src)
            timing["save_rate_ms"] = _elapsed_ms(save_started)
            message_queue.put(("log", f"금리 영역 이미지 저장: {rate_img_src}", "INFO"))
        else:
            timing["save_rate_ms"] = 0.0
            rate_img_src = screenshot_rate

    timing["capture_total_ms"] = _elapsed_ms(capture_started)
    return CaptureScreenshotsResult(date_img_src, rate_img_src, timing)
