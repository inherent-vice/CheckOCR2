"""Legacy OCR workflow adapters used by the Tk controller."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from .models import OcrRow
from .workflow import CapturedImages, OcrResult, WorkflowContext

type CaptureFunc = Callable[
    [str, str, Mapping[str, Any], float, float, bool],
    tuple[Any | None, Any | None],
]
type OcrProcessFunc = Callable[[Any, Any, bool], tuple[str, str]]


@dataclass
class LegacyAutomationAdapter:
    capture_screenshots: CaptureFunc
    save_folder: str
    coords: Mapping[str, Any]
    paste_delay: float
    load_delay: float
    save_detail_images: bool
    get_capture_timing: Callable[[], Mapping[str, Any]]
    row_timing_by_index: dict[int, dict[str, Any]]
    elapsed_ms: Callable[[float], float]
    now: Callable[[], float] = perf_counter

    def capture(self, row: OcrRow, context: WorkflowContext) -> CapturedImages | None:
        capture_started = self.now()
        date_img_src, rate_img_src = self.capture_screenshots(
            row.code,
            self.save_folder,
            self.coords,
            self.paste_delay,
            self.load_delay,
            self.save_detail_images,
        )
        capture_timing = dict(self.get_capture_timing())
        capture_timing.setdefault("capture_adapter_ms", self.elapsed_ms(capture_started))
        self.row_timing_by_index.setdefault(context.index, {})["capture_timing_ms"] = capture_timing
        if date_img_src is None or rate_img_src is None:
            return None
        return CapturedImages(date_img_src, rate_img_src, metadata={"timing_ms": capture_timing})


@dataclass
class LegacyEasyOcrAdapter:
    process_single_ocr: OcrProcessFunc
    save_detail_images: bool
    clear_ocr_tracking: Callable[[], None]
    get_ocr_timings: Callable[[], Mapping[str, Any]]
    get_ocr_confidences: Callable[[], Mapping[str, Any]]
    get_ocr_fallbacks: Callable[[], Mapping[str, Any]]
    row_timing_by_index: dict[int, dict[str, Any]]
    row_metadata_by_index: dict[int, dict[str, Any]]
    elapsed_ms: Callable[[float], float]
    now: Callable[[], float] = perf_counter

    def read(self, images: CapturedImages, row: OcrRow, context: WorkflowContext) -> OcrResult:
        ocr_started = self.now()
        self.clear_ocr_tracking()
        date_result, rate_result = self.process_single_ocr(
            images.date_image,
            images.rate_image,
            self.save_detail_images,
        )
        ocr_timing = dict(self.get_ocr_timings())
        ocr_timing.setdefault("ocr_adapter_ms", self.elapsed_ms(ocr_started))
        timing = self.row_timing_by_index.setdefault(context.index, {})
        timing["ocr_timing_ms"] = ocr_timing
        ocr_confidences = self.get_ocr_confidences()
        if ocr_confidences:
            self.row_metadata_by_index.setdefault(context.index, {})["ocr_confidence"] = dict(ocr_confidences)
        ocr_fallbacks = self.get_ocr_fallbacks()
        if ocr_fallbacks:
            self.row_metadata_by_index.setdefault(context.index, {})["ocr_fallback"] = dict(ocr_fallbacks)
        return OcrResult(date_result, rate_result, metadata={"timing_ms": timing})
