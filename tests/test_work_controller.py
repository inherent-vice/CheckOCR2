from __future__ import annotations


def test_work_controller_start_stop_skip_and_reset(ocr_module):
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
