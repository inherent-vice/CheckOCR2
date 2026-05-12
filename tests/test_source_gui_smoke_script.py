from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from scripts import package_smoke, source_gui_smoke


class FakeProcess:
    def __init__(self, pid: int = 100, return_code: int | None = None) -> None:
        self.pid = pid
        self.return_code = return_code
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True
        self.return_code = 0

    def kill(self) -> None:
        self.killed = True
        self.return_code = -9

    def wait(self, timeout: float | None = None) -> int:
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


def test_parse_args_accepts_string_entrypoint_and_requirements():
    args = source_gui_smoke.parse_args(
        [
            "--entrypoint",
            "python check_capture_ocr.py",
            "--isolated-appdata",
            "--require-ready",
            "--require-settings-file",
            "--min-window-width",
            "1000",
            "--min-window-height",
            "600",
        ]
    )

    assert args.entrypoint == "python check_capture_ocr.py"
    assert args.isolated_appdata is True
    assert args.require_ready is True
    assert args.require_settings_file is True
    assert args.min_window_width == 1000
    assert args.min_window_height == 600


def test_run_source_gui_smoke_reports_ready_and_settings_file(tmp_path):
    process = FakeProcess(pid=100)
    launched = []
    clock = FakeClock([0.0, 0.0, 1.25, 1.5])

    def launch(command: list[str], cwd: Path) -> FakeProcess:
        launched.append((command, cwd))
        status_file = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        appdata_dir = Path(os.environ["APPDATA"])
        settings_file = appdata_dir / "CheckOCR2" / "settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text("{}", encoding="utf-8")
        status_file.write_text(
            json.dumps(
                {
                    "runtime_state": "Ready",
                    "ocr_ready": True,
                    "settings_file": str(settings_file),
                }
            ),
            encoding="utf-8",
        )
        return process

    exit_code, report = source_gui_smoke.run_source_gui_smoke(
        "python check_capture_ocr.py",
        cwd=tmp_path,
        require_ready=True,
        require_settings_file=True,
        isolated_appdata=True,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(
                hwnd=10,
                pid=100,
                title="📊 Check Capture OCR V6.1",
                width=1200,
                height=850,
            )
        ],
        sleep=lambda _seconds: None,
        clock=clock,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["ocr_ready"] is True
    assert report["settings_file"].endswith(r"CheckOCR2\settings.json")
    assert report["appdata_cleanup"]["removed"] is True
    assert report["window_width"] == 1200
    assert report["window_height"] == 850
    assert launched == [(["python", "check_capture_ocr.py"], tmp_path)]
    assert process.terminated is True


def test_run_source_gui_smoke_can_require_minimum_window_size(tmp_path):
    process = FakeProcess(pid=100)

    exit_code, report = source_gui_smoke.run_source_gui_smoke(
        "python check_capture_ocr.py",
        cwd=tmp_path,
        min_window_width=1000,
        min_window_height=600,
        process_launcher=lambda _command, _cwd: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(
                hwnd=10,
                pid=100,
                title="📊 Check Capture OCR V6.1",
                width=1200,
                height=850,
            )
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["min_window_width"] == 1000
    assert report["min_window_height"] == 600


def test_run_source_gui_smoke_rejects_small_window_size(tmp_path):
    process = FakeProcess(pid=100)

    exit_code, report = source_gui_smoke.run_source_gui_smoke(
        "python check_capture_ocr.py",
        cwd=tmp_path,
        min_window_width=1000,
        process_launcher=lambda _command, _cwd: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(
                hwnd=10,
                pid=100,
                title="📊 Check Capture OCR V6.1",
                width=900,
                height=850,
            )
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "window_size_too_small"
    assert "below minimum 1000" in report["error"]


def test_run_source_gui_smoke_requires_ready_for_settings_file():
    exit_code, report = source_gui_smoke.run_source_gui_smoke(
        "python check_capture_ocr.py",
        require_settings_file=True,
    )

    assert exit_code == 2
    assert report["error_code"] == "settings_file_requires_ready"


def test_run_source_gui_smoke_reports_entrypoint_parse_failure():
    exit_code, report = source_gui_smoke.run_source_gui_smoke('"python check_capture_ocr.py')

    assert exit_code == 2
    assert report["error_code"] == "entrypoint_parse_failed"
    assert "No closing quotation" in report["error"]


def test_run_source_gui_smoke_reports_process_exit_before_window(tmp_path):
    process = FakeProcess(pid=100, return_code=7)

    exit_code, report = source_gui_smoke.run_source_gui_smoke(
        "python check_capture_ocr.py",
        cwd=tmp_path,
        process_launcher=lambda _command, _cwd: process,
        list_windows=lambda: [],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "process_exited"
    assert report["process_exit_code"] == 7


def test_run_source_gui_smoke_reports_launch_failure(tmp_path):
    def launch(_command: list[str], _cwd: Path) -> FakeProcess:
        raise OSError("cannot launch")

    exit_code, report = source_gui_smoke.run_source_gui_smoke(
        "python check_capture_ocr.py",
        cwd=tmp_path,
        process_launcher=launch,
        list_windows=lambda: [],
    )

    assert exit_code == 2
    assert report["status"] == "error"
    assert report["error_code"] == "launch_failed"
    assert report["error"] == "cannot launch"


def test_launch_source_entrypoint_uses_cwd_and_suppresses_stdio(monkeypatch, tmp_path):
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return FakeProcess(pid=123)

    monkeypatch.setattr(source_gui_smoke.subprocess, "Popen", fake_popen)

    process = source_gui_smoke.launch_source_entrypoint(["python", "-m", "checkocr2.main"], tmp_path)

    assert process.pid == 123
    assert calls == [
        (
            ["python", "-m", "checkocr2.main"],
            {
                "cwd": str(tmp_path),
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            },
        )
    ]
