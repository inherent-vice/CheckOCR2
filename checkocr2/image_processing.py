"""Image processing helpers for OCR crops."""

from __future__ import annotations

import os
from dataclasses import dataclass

from PIL import Image

from .models import Region

RESAMPLING_METHODS = {
    "LANCZOS": Image.Resampling.LANCZOS,
    "BICUBIC": Image.Resampling.BICUBIC,
    "BILINEAR": Image.Resampling.BILINEAR,
    "NEAREST": Image.Resampling.NEAREST,
}


@dataclass(frozen=True)
class UpscaledImage:
    image: Image.Image
    original_size: tuple[int, int]
    new_size: tuple[int, int]
    was_upscaled: bool


@dataclass(frozen=True)
class TempImageCleanup:
    removed: bool
    log_event: tuple[str, str] | None = None


def upscale_image(
    image: Image.Image,
    *,
    enabled: bool = True,
    factor: float = 2.0,
    method: str = "LANCZOS",
) -> Image.Image:
    """Return an upscaled copy of an image, or the original image when disabled."""

    if not enabled or factor <= 1.0:
        return image

    new_width = int(image.width * factor)
    new_height = int(image.height * factor)
    resampling = RESAMPLING_METHODS.get(method, Image.Resampling.LANCZOS)
    return image.resize((new_width, new_height), resampling)


def upscale_image_source(
    image_source: str | Image.Image,
    *,
    enabled: bool = True,
    factor: float = 2.0,
    method: str = "LANCZOS",
) -> UpscaledImage:
    image = Image.open(image_source) if isinstance(image_source, str) else image_source
    original_size = image.size
    upscaled_image = upscale_image(
        image,
        enabled=enabled,
        factor=factor,
        method=method,
    )
    return UpscaledImage(
        image=upscaled_image,
        original_size=original_size,
        new_size=upscaled_image.size,
        was_upscaled=upscaled_image is not image,
    )


def screenshot_region(region: Region) -> tuple[int, int, int, int]:
    """Convert a Region into the pyautogui screenshot tuple."""

    if not region.is_valid:
        raise ValueError(f"Invalid screenshot region: {region.as_tuple()}")
    return (region.x1, region.y1, region.width, region.height)


def cleanup_temp_ocr_image(
    image_source: str | object,
    *,
    save_details: bool,
    field_name: str,
    exists_func=os.path.exists,
    remove_func=os.remove,
) -> TempImageCleanup:
    if not isinstance(image_source, str) or save_details:
        return TempImageCleanup(False)
    if not exists_func(image_source):
        return TempImageCleanup(False)
    if "_date.png" not in image_source and "_rate.png" not in image_source:
        return TempImageCleanup(False)

    try:
        remove_func(image_source)
    except OSError as exc:
        return TempImageCleanup(
            False,
            (f"임시 {field_name} 이미지 파일 삭제 실패: {exc}", "WARNING"),
        )
    return TempImageCleanup(
        True,
        (f"임시 {field_name} 이미지 파일 삭제: {image_source}", "DEBUG"),
    )
