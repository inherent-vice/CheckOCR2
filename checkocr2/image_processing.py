"""Image processing helpers for OCR crops."""

from __future__ import annotations

from PIL import Image

from .models import Region

RESAMPLING_METHODS = {
    "LANCZOS": Image.Resampling.LANCZOS,
    "BICUBIC": Image.Resampling.BICUBIC,
    "BILINEAR": Image.Resampling.BILINEAR,
    "NEAREST": Image.Resampling.NEAREST,
}


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


def screenshot_region(region: Region) -> tuple[int, int, int, int]:
    """Convert a Region into the pyautogui screenshot tuple."""

    if not region.is_valid:
        raise ValueError(f"Invalid screenshot region: {region.as_tuple()}")
    return (region.x1, region.y1, region.width, region.height)
