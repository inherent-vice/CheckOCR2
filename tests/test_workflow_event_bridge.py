from __future__ import annotations

import queue

import pytest

from checkocr2.events import UiEvent, UiEventType
from checkocr2.workflow import grid_update_event
from checkocr2.workflow_event_bridge import WorkflowEventBridge


class DummyDataManager:
    current_processing_index = None


def test_workflow_event_bridge_records_processing_start_and_queues_event():
    events = queue.Queue()
    row_timing = {}
    now_values = iter([10.0])
    data_manager = DummyDataManager()
    bridge = WorkflowEventBridge(
        events,
        data_manager,
        row_timing,
        elapsed_ms=lambda started: started,
        now=lambda: next(now_values),
    )

    bridge.emit(grid_update_event("processing", 2))

    assert bridge.row_started_by_index == {2: 10.0}
    assert data_manager.current_processing_index == 2
    assert row_timing == {}
    assert events.get_nowait() == ("grid_update", ("processing", 2))


def test_workflow_event_bridge_records_complete_row_total_after_processing():
    events = queue.Queue()
    row_timing = {}
    clock = [1.25]

    def elapsed_ms(started):
        return round((clock[0] - started) * 1000, 3)

    bridge = WorkflowEventBridge(
        events,
        DummyDataManager(),
        row_timing,
        elapsed_ms=elapsed_ms,
        now=lambda: clock[0],
    )

    bridge.emit(grid_update_event("processing", 0))
    clock[0] = 2.75
    bridge.emit(grid_update_event("complete", 0, "2026/05/08", "3.500", "완료"))

    assert row_timing == {0: {"row_total_ms": 1500.0}}
    assert events.get_nowait() == ("grid_update", ("processing", 0))
    assert events.get_nowait() == ("grid_update", ("complete", 0, "2026/05/08", "3.500", "완료"))


def test_workflow_event_bridge_records_error_row_total_after_processing():
    events = queue.Queue()
    row_timing = {}
    clock = [4.0]
    bridge = WorkflowEventBridge(
        events,
        DummyDataManager(),
        row_timing,
        elapsed_ms=lambda started: clock[0] - started,
        now=lambda: clock[0],
    )

    bridge.emit(grid_update_event("processing", 3))
    clock[0] = 4.5
    bridge.emit(grid_update_event("error", 3, "캡처 실패"))

    assert row_timing == {3: {"row_total_ms": 0.5}}
    assert events.get_nowait() == ("grid_update", ("processing", 3))
    assert events.get_nowait() == ("grid_update", ("error", 3, "캡처 실패"))


def test_workflow_event_bridge_queues_completion_without_timing_when_not_started():
    events = queue.Queue()
    row_timing = {}
    bridge = WorkflowEventBridge(
        events,
        DummyDataManager(),
        row_timing,
        elapsed_ms=lambda started: started,
    )

    bridge.emit(grid_update_event("complete", 4, "", "", "완료"))

    assert row_timing == {}
    assert events.get_nowait() == ("grid_update", ("complete", 4, "", "", "완료"))


def test_workflow_event_bridge_forwards_non_grid_events_unchanged():
    events = queue.Queue()
    row_timing = {}
    bridge = WorkflowEventBridge(
        events,
        DummyDataManager(),
        row_timing,
        elapsed_ms=lambda started: started,
    )

    bridge.emit(UiEvent(UiEventType.LOG, ("message", "INFO")))

    assert row_timing == {}
    assert events.get_nowait() == ("log", "message", "INFO")


def test_workflow_event_bridge_raises_before_queueing_malformed_grid_update():
    events = queue.Queue()
    row_timing = {}
    bridge = WorkflowEventBridge(
        events,
        DummyDataManager(),
        row_timing,
        elapsed_ms=lambda started: started,
    )

    malformed_event = UiEvent(UiEventType.GRID_UPDATE, (("processing",),))

    with pytest.raises(ValueError, match="requires update type and row index"):
        bridge.emit(malformed_event)

    assert row_timing == {}
    assert events.empty()
