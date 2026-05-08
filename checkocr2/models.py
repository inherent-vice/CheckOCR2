"""Typed data models for CheckOCR2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CODE_COL = "종목코드"
NAME_COL = "종목명"
DATE_COL = "날짜"
RATE_COL = "금리"
STATUS_COL = "상태"

STATUS_WAITING = "대기 중"
STATUS_PROCESSING = "처리 중..."
STATUS_DONE = "완료"
STATUS_STOPPED = "중단됨"


@dataclass(frozen=True)
class Region:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def is_valid(self) -> bool:
        return self.width > 0 and self.height > 0

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass(frozen=True)
class CaptureAreas:
    click_point: tuple[int, int]
    all_area: Region
    date_area: Region
    rate_area: Region


@dataclass(frozen=True)
class Delays:
    paste: float = 0.5
    loading: float = 2.5


@dataclass(frozen=True)
class UpscalingOptions:
    enabled: bool = True
    factor: float = 2.0
    method: str = "LANCZOS"


@dataclass(frozen=True)
class OcrOptions:
    save_detail_images: bool = True
    skip_kbp_code: bool = True
    upscaling: UpscalingOptions = field(default_factory=UpscalingOptions)


@dataclass
class OcrRow:
    code: str = ""
    name: str = ""
    date: str = ""
    rate: str = ""
    status: str = STATUS_WAITING

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> OcrRow:
        return cls(
            code=str(row.get(CODE_COL, "") or ""),
            name=str(row.get(NAME_COL, "") or ""),
            date=str(row.get(DATE_COL, "") or ""),
            rate=str(row.get(RATE_COL, "") or ""),
            status=str(row.get(STATUS_COL, STATUS_WAITING) or STATUS_WAITING),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            CODE_COL: self.code,
            NAME_COL: self.name,
            DATE_COL: self.date,
            RATE_COL: self.rate,
            STATUS_COL: self.status,
        }


@dataclass(frozen=True)
class RunSummary:
    processed_count: int
    total_items: int
    blank_date_count: int = 0
    blank_rate_count: int = 0
