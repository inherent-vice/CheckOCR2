from __future__ import annotations

from checkocr2.worker import start_daemon_worker


def test_start_daemon_worker_runs_target_and_exposes_handle():
    calls = []

    handle = start_daemon_worker(calls.append, "done", name="unit-worker")
    handle.join(timeout=5)

    assert calls == ["done"]
    assert handle.thread.daemon is True
    assert handle.thread.name == "unit-worker"
    assert handle.is_alive is False
