"""Tk-free workflow seam for package-level OCR orchestration."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, MutableMapping
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

from .events import UiEvent, UiEventType, log_event
from .models import (
    DATE_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_DONE,
    STATUS_PROCESSING,
    STATUS_STOPPED,
    STATUS_WAITING,
    OcrRow,
)

ERROR_CAPTURE_FAILED = "캡처 실패"
ERROR_MISSING_CODE = "종목코드 없음"
ERROR_PROCESSING = "처리 오류"
ERROR_SKIPPED = "건너뜀"

type GridRow = MutableMapping[str, Any] | OcrRow
type EventSink = Callable[[UiEvent], None]


@dataclass(frozen=True)
class WorkflowOptions:
    skip_kbp_code: bool = True
    save_detail_images: bool = True
    output_dir: str = ""
    input_excel_path: str = ""


@dataclass(frozen=True)
class WorkflowContext:
    index: int
    total_items: int
    output_dir: str = ""
    input_excel_path: str = ""
    save_detail_images: bool = True


@dataclass(frozen=True)
class CapturedImages:
    date_image: Any | None
    rate_image: Any | None
    all_image: Any | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return self.date_image is not None and self.rate_image is not None


@dataclass(frozen=True)
class OcrResult:
    date: str = ""
    rate: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinalizationIntent:
    output_dir: str
    input_excel_path: str
    processed_count: int
    total_items: int

    def as_event(self) -> UiEvent:
        return finalize_export_event(
            self.output_dir,
            self.input_excel_path,
            self.processed_count,
            self.total_items,
        )


@dataclass(frozen=True)
class WorkflowResult:
    processed_count: int
    total_items: int
    stopped: bool = False
    finalization_intent: FinalizationIntent | None = None


@dataclass
class WorkflowStopToken:
    is_stopped: bool = False
    skip_current: bool = False
    current_item: str = ""

    def stop(self) -> None:
        self.is_stopped = True

    def skip(self) -> None:
        self.skip_current = True

    def reset_current_skip(self) -> None:
        self.skip_current = False


class AutomationAdapter(Protocol):
    def capture(self, row: OcrRow, context: WorkflowContext) -> CapturedImages | None: ...


class OcrAdapter(Protocol):
    def read(self, images: CapturedImages, row: OcrRow, context: WorkflowContext) -> OcrResult: ...


@dataclass
class EventRecorder:
    events: list[UiEvent] = field(default_factory=list)

    def emit(self, event: UiEvent) -> None:
        self.events.append(event)

    def legacy_tuples(self) -> list[tuple[Any, ...]]:
        return [event.as_legacy_tuple() for event in self.events]


@dataclass
class FakeAutomationAdapter:
    capture_by_code: dict[str, CapturedImages | None | BaseException] = field(default_factory=dict)
    calls: list[tuple[OcrRow, WorkflowContext]] = field(default_factory=list)

    def capture(self, row: OcrRow, context: WorkflowContext) -> CapturedImages | None:
        self.calls.append((row, context))
        outcome = self.capture_by_code.get(row.code, CapturedImages("date-image", "rate-image"))
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@dataclass
class FakeOcrAdapter:
    result_by_code: dict[str, OcrResult | BaseException] = field(default_factory=dict)
    default_result: OcrResult = field(default_factory=OcrResult)
    calls: list[tuple[CapturedImages, OcrRow, WorkflowContext]] = field(default_factory=list)

    def read(self, images: CapturedImages, row: OcrRow, context: WorkflowContext) -> OcrResult:
        self.calls.append((images, row, context))
        outcome = self.result_by_code.get(row.code, self.default_result)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@dataclass
class WorkflowRunner:
    automation: AutomationAdapter
    ocr: OcrAdapter
    stop_token: Any | None = None
    event_sink: EventSink | None = None
    events: list[UiEvent] = field(default_factory=list)

    def process_rows(
        self,
        rows: Iterable[GridRow],
        options: WorkflowOptions | None = None,
    ) -> WorkflowResult:
        row_list = list(rows)
        total_items = len(row_list)
        run_options = options or WorkflowOptions()
        processed_count = 0

        for index, source_row in enumerate(row_list):
            if self._is_stopped():
                self._emit_stopped()
                return WorkflowResult(processed_count, total_items, stopped=True)

            row = _row_snapshot(source_row)
            self._set_current_item(row)
            self._set_skip_current(False)
            _set_status(source_row, STATUS_PROCESSING)
            self._emit(grid_update_event("processing", index))

            if run_options.skip_kbp_code and row.code.lower().startswith("kbp"):
                _set_result(source_row, "", "", STATUS_DONE)
                self._emit(log_event(f"[{row.code}] KBP code skipped by workflow setting.", "INFO"))
                self._emit(grid_update_event("complete", index, "", "", STATUS_DONE))
                processed_count += 1
                continue

            if not row.code:
                _set_status(source_row, ERROR_MISSING_CODE)
                self._emit(log_event(f"Row {index + 1} skipped because code is blank.", "WARNING"))
                self._emit(grid_update_event("error", index, ERROR_MISSING_CODE))
                continue

            context = WorkflowContext(
                index=index,
                total_items=total_items,
                output_dir=run_options.output_dir,
                input_excel_path=run_options.input_excel_path,
                save_detail_images=run_options.save_detail_images,
            )
            images = self._capture(row, context)

            if self._skip_requested():
                _set_status(source_row, ERROR_SKIPPED)
                self._emit(log_event(f"[{row.code}] skipped by current-item request.", "INFO"))
                self._emit(grid_update_event("error", index, ERROR_SKIPPED))
                continue

            if self._is_stopped():
                self._emit_stopped()
                return WorkflowResult(processed_count, total_items, stopped=True)

            if images is None or not images.is_complete:
                _set_status(source_row, ERROR_CAPTURE_FAILED)
                self._emit(grid_update_event("error", index, ERROR_CAPTURE_FAILED))
                continue

            result = self._read_ocr(images, row, context)
            if result is None:
                _set_status(source_row, ERROR_PROCESSING)
                self._emit(grid_update_event("error", index, ERROR_PROCESSING))
                continue

            if self._is_stopped():
                self._emit_stopped()
                return WorkflowResult(processed_count, total_items, stopped=True)

            update_started = perf_counter()
            _set_result(source_row, result.date, result.rate, STATUS_DONE)
            self._emit(grid_update_event("complete", index, result.date, result.rate, STATUS_DONE))
            _record_update_timing(result, _elapsed_ms(update_started))
            self._emit(log_event(f"[{row.code}] complete - date: '{result.date}', rate: '{result.rate}'", "SUCCESS"))
            processed_count += 1

        intent = FinalizationIntent(
            run_options.output_dir,
            run_options.input_excel_path,
            processed_count,
            total_items,
        )
        self._emit(intent.as_event())
        return WorkflowResult(processed_count, total_items, finalization_intent=intent)

    def _capture(self, row: OcrRow, context: WorkflowContext) -> CapturedImages | None:
        try:
            return self.automation.capture(row, context)
        except Exception as exc:
            self._emit(log_event(f"[{row.code}] capture failed: {exc}", "ERROR"))
            return None

    def _read_ocr(self, images: CapturedImages, row: OcrRow, context: WorkflowContext) -> OcrResult | None:
        try:
            return self.ocr.read(images, row, context)
        except Exception as exc:
            self._emit(log_event(f"[{row.code}] OCR failed: {exc}", "ERROR"))
            return None

    def _emit(self, event: UiEvent) -> None:
        self.events.append(event)
        if self.event_sink is not None:
            self.event_sink(event)

    def _emit_stopped(self) -> None:
        self._emit(log_event("Workflow stopped.", "INFO"))
        self._emit(stopped_event())

    def _is_stopped(self) -> bool:
        return bool(getattr(self.stop_token, "is_stopped", False))

    def _skip_requested(self) -> bool:
        return bool(getattr(self.stop_token, "skip_current", False))

    def _set_skip_current(self, value: bool) -> None:
        if self.stop_token is not None and hasattr(self.stop_token, "skip_current"):
            self.stop_token.skip_current = value

    def _set_current_item(self, row: OcrRow) -> None:
        if self.stop_token is not None and hasattr(self.stop_token, "current_item"):
            current_item = f"{row.code} ({row.name})" if row.code or row.name else ""
            self.stop_token.current_item = current_item

    def legacy_tuples(self) -> list[tuple[Any, ...]]:
        return [event.as_legacy_tuple() for event in self.events]


def grid_update_event(update_type: str, index: int, *payload: Any) -> UiEvent:
    return UiEvent(UiEventType.GRID_UPDATE, ((update_type, index, *payload),))


def stopped_event() -> UiEvent:
    return UiEvent(UiEventType.STOPPED, (None,))


def finalize_export_event(
    output_dir: str,
    input_excel_path: str,
    processed_count: int,
    total_items: int,
) -> UiEvent:
    return UiEvent(
        UiEventType.FINALIZE_EXPORT_AND_COMPLETE,
        (output_dir, input_excel_path, processed_count, total_items),
    )


def finalize_processing_states(rows: Iterable[GridRow]) -> int:
    changed_count = 0
    for row in rows:
        if _row_status(row) in {STATUS_WAITING, STATUS_PROCESSING}:
            _set_status(row, STATUS_STOPPED)
            changed_count += 1
    return changed_count


def _row_snapshot(row: GridRow) -> OcrRow:
    if isinstance(row, OcrRow):
        return OcrRow(row.code, row.name, row.date, row.rate, row.status)
    return OcrRow.from_dict(row)


def _row_status(row: GridRow) -> str:
    if isinstance(row, OcrRow):
        return row.status
    return str(row.get(STATUS_COL, STATUS_WAITING) or STATUS_WAITING)


def _set_status(row: GridRow, status: str) -> None:
    if isinstance(row, OcrRow):
        row.status = status
    else:
        row[STATUS_COL] = status


def _set_result(row: GridRow, date: str, rate: str, status: str) -> None:
    if isinstance(row, OcrRow):
        row.date = date
        row.rate = rate
        row.status = status
    else:
        row[DATE_COL] = date
        row[RATE_COL] = rate
        row[STATUS_COL] = status


def _record_update_timing(result: OcrResult, update_ms: float) -> None:
    timing = result.metadata.get("timing_ms")
    if isinstance(timing, MutableMapping):
        timing["update_ms"] = update_ms


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


__all__ = [
    "AutomationAdapter",
    "CapturedImages",
    "ERROR_CAPTURE_FAILED",
    "ERROR_MISSING_CODE",
    "ERROR_PROCESSING",
    "ERROR_SKIPPED",
    "EventRecorder",
    "FakeAutomationAdapter",
    "FakeOcrAdapter",
    "FinalizationIntent",
    "OcrAdapter",
    "OcrResult",
    "WorkflowContext",
    "WorkflowOptions",
    "WorkflowResult",
    "WorkflowRunner",
    "WorkflowStopToken",
    "finalize_export_event",
    "finalize_processing_states",
    "grid_update_event",
    "stopped_event",
]
