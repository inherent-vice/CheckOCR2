from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from scripts import package_smoke


class FakeProcess:
    def __init__(
        self,
        pid: int = 100,
        return_code: int | None = None,
        wait_timeout_once: bool = False,
    ) -> None:
        self.pid = pid
        self.return_code = return_code
        self.wait_timeout_once = wait_timeout_once
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True
        if not self.wait_timeout_once:
            self.return_code = 0

    def kill(self) -> None:
        self.killed = True
        self.return_code = -9

    def wait(self, timeout: float | None = None) -> int:
        if self.wait_timeout_once:
            self.wait_timeout_once = False
            raise subprocess.TimeoutExpired("fake.exe", timeout)
        if self.return_code is None:
            self.return_code = 0
        return self.return_code


class FakeClock:
    def __init__(self, values: list[float]) -> None:
        self.values = values
        self.last_value = values[-1]

    def __call__(self) -> float:
        if self.values:
            self.last_value = self.values.pop(0)
        return self.last_value


def touch_exe(tmp_path: Path) -> Path:
    exe_path = tmp_path / "CheckCaptureOCR_V6.1.exe"
    exe_path.write_text("placeholder", encoding="utf-8")
    return exe_path


def write_metadata_for_exe(exe_path: Path) -> dict[str, str]:
    metadata = {
        "app_version": "6.1.0",
        "build_date": "2026-05-08T00:00:00+00:00",
        "python_version": "3.12.6",
        "dependency_hash": "abc123",
    }
    metadata_path = exe_path.parent / "_internal" / "checkocr2" / "build_metadata.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return metadata


def test_find_matching_window_filters_to_launched_process():
    windows = [
        package_smoke.WindowInfo(hwnd=1, pid=200, title="Check Capture OCR old instance"),
        package_smoke.WindowInfo(hwnd=2, pid=100, title="Check Capture OCR V6.1"),
    ]

    match = package_smoke.find_matching_window(
        "Check Capture OCR",
        process_id=100,
        list_windows=lambda: windows,
    )

    assert match == windows[1]


def test_run_package_smoke_reports_ok_and_terminates(tmp_path):
    exe_path = touch_exe(tmp_path)
    metadata = write_metadata_for_exe(exe_path)
    process = FakeProcess(pid=100)

    def launch(path: Path) -> FakeProcess:
        assert path == exe_path
        return process

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["window_title"] == "Check Capture OCR V6.1"
    assert report["window_pid"] == 100
    assert report["window_hwnd"] == 10
    assert report["package_metadata"] == metadata
    assert report["package_size_mb"] >= 0
    assert report["termination"] == {"terminated": True, "killed": False, "exit_code": 0}
    assert process.terminated
    assert not process.killed


def test_run_package_smoke_can_require_packaged_metadata(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_package_metadata=True,
        process_launcher=lambda _path: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "metadata_missing"
    assert report["package_metadata"] is None


def test_run_package_smoke_can_require_ocr_ready_status(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)

    def launch(_path: Path) -> FakeProcess:
        assert os.environ[package_smoke.PACKAGE_SMOKE_FAST_OCR_ENV] == "1"
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
            json.dumps({"runtime_state": "Ready", "ocr_ready": True}),
            encoding="utf-8",
        )
        return process

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["ocr_ready_required"] is True
    assert report["ocr_ready"] is True
    assert report["ocr_ready_status"]["runtime_state"] == "Ready"
    assert package_smoke.PACKAGE_SMOKE_FAST_OCR_ENV not in os.environ
    assert package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV not in os.environ


def test_run_package_smoke_reports_ocr_ready_timeout(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    clock = FakeClock([0.0, 0.0, 0.0, 0.0, 2.0])

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        ocr_ready_timeout_seconds=1.0,
        poll_interval_seconds=0.1,
        process_launcher=lambda _path: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
        clock=clock,
    )

    assert exit_code == 1
    assert report["status"] == "ocr_ready_timeout"
    assert report["error"] == "Timed out waiting for OCR Ready status"


def test_run_package_smoke_times_out_and_terminates(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    clock = FakeClock([0.0, 0.0, 2.0, 2.0])

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        timeout_seconds=1.0,
        poll_interval_seconds=0.1,
        process_launcher=lambda _path: process,
        list_windows=lambda: [],
        sleep=lambda _seconds: None,
        clock=clock,
    )

    assert exit_code == 1
    assert report["status"] == "timeout"
    assert report["error"] == "Timed out waiting for a matching window title"
    assert report["termination"] == {"terminated": True, "killed": False, "exit_code": 0}
    assert process.terminated


def test_run_package_smoke_reports_process_exit_before_window(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100, return_code=7)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        process_launcher=lambda _path: process,
        list_windows=lambda: [],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "process_exited"
    assert report["process_exit_code"] == 7
    assert report["termination"] == {"terminated": False, "killed": False, "exit_code": 7}
    assert not process.terminated


def test_run_package_smoke_reports_missing_exe_without_launching(tmp_path):
    missing_exe = tmp_path / "missing.exe"

    exit_code, report = package_smoke.run_package_smoke(missing_exe)

    assert exit_code == 2
    assert report["status"] == "error"
    assert report["error_code"] == "exe_not_found"
    assert report["exe_path"] == str(missing_exe)


def test_main_prints_json_status(monkeypatch, capsys, tmp_path):
    exe_path = touch_exe(tmp_path)

    def fake_run(exe_path_arg: Path, **_kwargs):
        return 0, {"status": "ok", "exe_path": str(exe_path_arg)}

    monkeypatch.setattr(package_smoke, "run_package_smoke", fake_run)

    exit_code = package_smoke.main([str(exe_path), "--timeout", "1", "--poll-interval", "0.1"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"status": "ok", "exe_path": str(exe_path)}
