"""Tk overlay windows for capture coordinate selection and preview."""

from __future__ import annotations

import os
import tkinter as tk
from typing import Any


def apply_overlay_icon(window: tk.Toplevel, master: Any) -> None:
    try:
        if hasattr(master, "_icon_photos") and master._icon_photos:
            window.iconphoto(True, *master._icon_photos)
        elif os.path.exists("eye_ocr_02_scanline.ico"):
            window.iconbitmap("eye_ocr_02_scanline.ico")
    except (OSError, tk.TclError):
        pass


def close_overlay_on_escape(window: Any, event: Any) -> str | None:
    if getattr(event, "keysym", None) == "Escape":
        window.destroy()
        return "break"
    return None


class AreaVisualizationOverlay(tk.Toplevel):
    def __init__(self, master: Any, areas_info: dict[str, Any], theme_manager: Any, auto_close: bool = True) -> None:
        super().__init__(master)
        self.master = master
        self.areas_info = areas_info
        self.theme_manager = theme_manager
        self.auto_close = auto_close

        apply_overlay_icon(self, master)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        overlay_bg = self.theme_manager.get_color("dark", "black")
        self.configure(bg=overlay_bg)
        self.attributes("-alpha", 0.7)

        self.canvas = tk.Canvas(self, bg=overlay_bg, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.draw_areas()

        if auto_close:
            self.after(3000, self.destroy)

        self.bind("<KeyPress>", self.on_key_press)
        self.focus_set()

    def draw_areas(self) -> None:
        colors = [
            self.theme_manager.get_color("danger"),
            self.theme_manager.get_color("primary"),
            self.theme_manager.get_color("success"),
            self.theme_manager.get_color("warning"),
        ]
        labels = ["클릭 포인트", "전체 영역", "날짜 영역", "금리 영역"]
        text_color = self.theme_manager.get_color("white", "white")

        if "click_point" in self.areas_info:
            x, y = self.areas_info["click_point"]
            r = 10
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=colors[0], outline=text_color, width=3)
            self.canvas.create_text(x, y - 25, text=labels[0], fill=text_color, font=("Arial", 12, "bold"))

        area_keys = ["all_area", "date_area", "rate_area"]
        for index, key in enumerate(area_keys):
            if key in self.areas_info and self.areas_info[key]:
                x1, y1, x2, y2 = self.areas_info[key]
                color = colors[index + 1]
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=4, fill="")
                center_x = (x1 + x2) // 2
                center_y = y1 - 20 if y1 > 30 else y2 + 20
                self.canvas.create_text(center_x, center_y, text=labels[index + 1], fill=color, font=("Arial", 14, "bold"))
                width, height = x2 - x1, y2 - y1
                self.canvas.create_text(center_x, center_y + 20, text=f"{width}x{height}", fill=text_color, font=("Arial", 10))

        screen_width = self.winfo_screenwidth()
        info_text = "설정된 영역들이 표시됩니다"
        if self.auto_close:
            info_text += " (3초 후 자동 종료)"
        info_text += " | ESC: 종료"
        self.canvas.create_text(screen_width // 2, 50, text=info_text, fill=text_color, font=("Arial", 16, "bold"))

    def on_key_press(self, event: Any) -> None:
        close_overlay_on_escape(self, event)


class DragCaptureOverlay(tk.Toplevel):
    def __init__(self, master: Any = None, color_key: str = "danger", theme_manager: Any = None) -> None:
        super().__init__(master)
        self.master = master
        self.theme_manager = theme_manager
        self.color = self.theme_manager.get_color(color_key, "red")

        apply_overlay_icon(self, master)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        overlay_bg = self.theme_manager.get_color("dark", "black")
        self.configure(bg=overlay_bg)
        self.attributes("-alpha", 0.3)

        self.canvas = tk.Canvas(self, bg=overlay_bg, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.start_x, self.start_y = None, None
        self.rect_id = None
        self.x1, self.y1, self.x2, self.y2 = None, None, None, None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<KeyPress-Escape>", lambda event: close_overlay_on_escape(self, event))

    def on_button_press(self, event: Any) -> None:
        self.start_x, self.start_y = event.x, event.y
        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline=self.color,
            width=2,
        )

    def on_move_press(self, event: Any) -> None:
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event: Any) -> None:
        end_x, end_y = event.x, event.y
        self.x1, self.y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        self.x2, self.y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        self.destroy()


class PointCaptureOverlay(tk.Toplevel):
    def __init__(self, master: Any = None, color_key: str = "danger", theme_manager: Any = None) -> None:
        super().__init__(master)
        self.master = master
        self.theme_manager = theme_manager
        self.color = self.theme_manager.get_color(color_key, "red")

        apply_overlay_icon(self, master)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        overlay_bg = self.theme_manager.get_color("dark", "black")
        self.configure(bg=overlay_bg)
        self.attributes("-alpha", 0.3)

        self.canvas = tk.Canvas(self, bg=overlay_bg, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.click_x, self.click_y = None, None
        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.bind("<KeyPress-Escape>", lambda event: close_overlay_on_escape(self, event))

    def on_click(self, event: Any) -> None:
        self.click_x, self.click_y = event.x, event.y
        r = 5
        self.canvas.create_oval(
            self.click_x - r,
            self.click_y - r,
            self.click_x + r,
            self.click_y + r,
            fill=self.color,
            outline=self.color,
        )
        self.after(100, self.destroy)
