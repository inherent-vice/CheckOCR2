from __future__ import annotations

from checkocr2.models import OcrRow
from checkocr2.work_controller import WorkStateSnapshot
from checkocr2.workflow import CapturedImages, FakeOcrAdapter, WorkflowRunner


def test_work_controller_start_stop_skip_and_reset(ocr_module):
    assert ocr_module.WorkController.__module__ == "checkocr2.work_controller"
    controller = ocr_module.WorkController()

    assert controller.is_stopped is False
    assert controller.is_running is False
    assert controller.skip_current is False
    assert controller.stop_event.is_set() is False

    controller.start_work()

    assert controller.is_stopped is False
    assert controller.is_running is True
    assert controller.skip_current is False
    assert controller.stop_event.is_set() is False

    controller.current_item = "ABC123"
    skip_message = controller.skip_current_item()

    assert controller.skip_current is True
    assert "ABC123" in skip_message

    stop_message = controller.stop_work()

    assert stop_message
    assert controller.is_stopped is True
    assert controller.is_running is False
    assert controller.stop_event.is_set() is True

    controller.reset()

    assert controller.is_stopped is False
    assert controller.is_running is False
    assert controller.skip_current is False
    assert controller.current_item == ""
    assert controller.stop_event.is_set() is False


def test_work_controller_snapshot_tracks_stop_skip_state(ocr_module):
    controller = ocr_module.WorkController()

    assert controller.snapshot() == WorkStateSnapshot(
        is_stopped=False,
        is_running=False,
        skip_current=False,
        current_item="",
        stop_event_is_set=False,
    )

    controller.start_work()
    controller.set_current_item("ABC123")
    controller.skip_current_item()
    snapshot = controller.snapshot()

    assert snapshot.is_running is True
    assert snapshot.skip_current is True
    assert snapshot.current_item == "ABC123"
    assert snapshot.stop_event_is_set is False

    controller.stop_work()

    assert controller.snapshot() == WorkStateSnapshot(
        is_stopped=True,
        is_running=False,
        skip_current=True,
        current_item="ABC123",
        stop_event_is_set=True,
    )


def test_workflow_runner_uses_work_controller_locked_state(ocr_module):
    class StopAfterCapture:
        def __init__(self, controller):
            self.controller = controller

        def capture(self, row, context):
            self.controller.stop_work()
            return CapturedImages("date-image", "rate-image")

    controller = ocr_module.WorkController()
    controller.start_work()
    runner = WorkflowRunner(
        StopAfterCapture(controller),
        FakeOcrAdapter(),
        stop_token=controller,
    )

    result = runner.process_rows([OcrRow("A001", "Name")])

    assert result.stopped is True
    snapshot = controller.snapshot()
    assert snapshot.current_item == "A001 (Name)"
    assert snapshot.is_stopped is True
    assert snapshot.is_running is False
