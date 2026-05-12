"""Bridge Tk-free workflow events back to the legacy Tk queue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from .events import UiEvent, parse_legacy_grid_update


@dataclass
class WorkflowEventBridge:
    message_queue: Any
    data_manager: Any
    row_timing_by_index: dict[int, dict[str, Any]]
    elapsed_ms: Callable[[float], float]
    now: Callable[[], float] = perf_counter
    row_started_by_index: dict[int, float] = field(default_factory=dict)

    def emit(self, event: UiEvent) -> None:
        legacy_event = event.as_legacy_tuple()
        if legacy_event[0] == "grid_update":
            self._record_grid_update(legacy_event[1])
        self.message_queue.put(legacy_event)

    def _record_grid_update(self, payload: object) -> None:
        grid_update = parse_legacy_grid_update(payload)
        row_index = grid_update.row_index
        if grid_update.update_type == "processing":
            self.row_started_by_index[row_index] = self.now()
            self.data_manager.current_processing_index = row_index
        elif grid_update.update_type in {"complete", "error"} and row_index in self.row_started_by_index:
            self.row_timing_by_index.setdefault(row_index, {})["row_total_ms"] = self.elapsed_ms(
                self.row_started_by_index[row_index]
            )
