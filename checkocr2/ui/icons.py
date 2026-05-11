"""Application icon helpers for the Tk shell."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable, Iterable
from typing import Any

ICO_CANDIDATES = ("eye_ocr_02_scanline.ico", "app_icon.ico")
PNG_CANDIDATES = ("eye_ocr_02_scanline.png", "app_icon.png")
ICON_SIZES = (16, 32, 48)


def first_existing_path(
    candidates: Iterable[str],
    *,
    exists: Callable[[str], bool] = os.path.exists,
) -> str | None:
    for path in candidates:
        if exists(path):
            return path
    return None


def build_png_icon_photos(
    png_path: str,
    *,
    icon_sizes: Iterable[int] = ICON_SIZES,
    image_open: Callable[[str], Any] | None = None,
    photo_factory: Callable[[Any], Any] | None = None,
) -> list[Any]:
    if image_open is None or photo_factory is None:
        from PIL import Image, ImageTk

        image_open = Image.open
        photo_factory = ImageTk.PhotoImage
        resample_filter = Image.Resampling.LANCZOS
    else:
        from PIL import Image

        resample_filter = Image.Resampling.LANCZOS

    pil_image = image_open(png_path)
    return [
        photo_factory(pil_image.resize((size, size), resample_filter))
        for size in icon_sizes
    ]


def apply_application_icon(
    window: Any,
    *,
    exists: Callable[[str], bool] = os.path.exists,
    print_func: Callable[[str], None] = print,
    image_open: Callable[[str], Any] | None = None,
    photo_factory: Callable[[Any], Any] | None = None,
) -> None:
    try:
        ico_path = first_existing_path(ICO_CANDIDATES, exists=exists)
        if ico_path:
            window.iconbitmap(ico_path)
            print_func(f"ICO 아이콘 설정 완료: {ico_path}")

        png_path = first_existing_path(PNG_CANDIDATES, exists=exists)
        if png_path:
            try:
                photo_images = build_png_icon_photos(
                    png_path,
                    image_open=image_open,
                    photo_factory=photo_factory,
                )
                window._icon_photos = photo_images
                if photo_images:
                    window.iconphoto(True, *photo_images)
                    print_func(
                        f"PNG 아이콘 설정 완료: {png_path} ({len(photo_images)}개 크기)"
                    )
            except ImportError:
                print_func(
                    "PIL 라이브러리를 찾을 수 없어 PNG 아이콘 설정을 건너뜁니다."
                )
            except (OSError, tk.TclError) as exc:
                print_func(f"PNG 아이콘 설정 중 오류: {exc}")

        if not ico_path and not png_path:
            print_func("아이콘 파일을 찾을 수 없습니다.")

    except (OSError, tk.TclError) as exc:
        print_func(f"아이콘 설정 중 전체 오류: {exc}")
