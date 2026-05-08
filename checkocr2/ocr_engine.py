"""OCR engine adapter seam."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class EasyOcrReaderLike(Protocol):
    def readtext(self, image, detail: int = 0, **kwargs: Any): ...


def create_easyocr_reader(languages: Sequence[str], *, gpu: bool = False) -> EasyOcrReaderLike:
    import easyocr

    return easyocr.Reader(list(languages), gpu=gpu)


def read_ocr_text(reader: EasyOcrReaderLike, image, *, detail: int = 0, allowlist: str | None = None):
    kwargs: dict[str, Any] = {"detail": detail}
    if allowlist is not None:
        kwargs["allowlist"] = allowlist
    return reader.readtext(image, **kwargs)
