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


def write_metadata_for_exe(exe_path: Path) -> dict[str, object]:
    metadata = {
        "app_version": "6.1.0",
        "build_date": "2026-05-08T00:00:00+00:00",
        "dependencies": {
            "opencv-python-headless": "4.10.0.84",
        },
        "python_version": "3.12.6",
        "dependency_hash": "abc123",
    }
    metadata_path = exe_path.parent / "_internal" / "checkocr2" / "build_metadata.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return metadata


def write_dist_info_for_exe(
    exe_path: Path, package_name: str, version: str = "4.10.0.84"
) -> Path:
    dist_dir_name = f"{package_name.replace('-', '_')}-{version}.dist-info"
    dist_info_path = exe_path.parent / "_internal" / dist_dir_name
    dist_info_path.mkdir(parents=True, exist_ok=True)
    dist_info_path.joinpath("METADATA").write_text(
        f"Name: {package_name}\nVersion: {version}\n",
        encoding="utf-8",
    )
    return dist_info_path


def test_find_matching_window_filters_to_launched_process():
    windows = [
        package_smoke.WindowInfo(
            hwnd=1, pid=200, title="Check Capture OCR old instance"
        ),
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
            package_smoke.WindowInfo(
                hwnd=10,
                pid=100,
                title="Check Capture OCR V6.1",
                width=1200,
                height=850,
            )
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["window_title"] == "Check Capture OCR V6.1"
    assert report["window_pid"] == 100
    assert report["window_hwnd"] == 10
    assert report["window_width"] == 1200
    assert report["window_height"] == 850
    assert report["package_metadata"] == metadata
    assert report["package_size_mb"] >= 0
    assert report["termination"] == {
        "terminated": True,
        "killed": False,
        "exit_code": 0,
    }
    assert process.terminated
    assert not process.killed


def test_run_package_smoke_can_require_minimum_window_size(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        min_window_width=1000,
        min_window_height=600,
        process_launcher=lambda _path: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(
                hwnd=10,
                pid=100,
                title="Check Capture OCR V6.1",
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


def test_run_package_smoke_rejects_small_window_size(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        min_window_width=1000,
        min_window_height=600,
        process_launcher=lambda _path: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(
                hwnd=10,
                pid=100,
                title="Check Capture OCR V6.1",
                width=900,
                height=850,
            )
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "window_size_too_small"
    assert report["window_width"] == 900
    assert "below minimum 1000" in report["error"]


def test_run_package_smoke_accepts_package_size_within_budget(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        max_package_size_mb=1.0,
        process_launcher=lambda _path: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["max_package_size_mb"] == 1.0


def test_run_package_smoke_reports_package_size_exceeded(tmp_path):
    exe_path = touch_exe(tmp_path)
    exe_path.parent.joinpath("large.bin").write_bytes(b"0" * (2 * 1024 * 1024))
    process = FakeProcess(pid=100)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        max_package_size_mb=1.0,
        process_launcher=lambda _path: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "package_size_exceeded"
    assert report["package_size_mb"] > 1.0
    assert "exceeds budget 1.0 MB" in report["error"]


def test_run_package_smoke_accepts_startup_time_within_budget(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    clock = FakeClock([0.0, 0.0, 1.0])

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        max_startup_seconds=5.0,
        process_launcher=lambda _path: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
        clock=clock,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["elapsed_seconds"] == 1.0
    assert report["max_startup_seconds"] == 5.0


def test_run_package_smoke_reports_startup_time_exceeded(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    clock = FakeClock([0.0, 0.0, 6.0])

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        max_startup_seconds=5.0,
        process_launcher=lambda _path: process,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
        clock=clock,
    )

    assert exit_code == 1
    assert report["status"] == "startup_time_exceeded"
    assert report["elapsed_seconds"] == 6.0
    assert "exceeds budget 5.0 seconds" in report["error"]


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


def test_run_package_smoke_requires_headless_opencv_metadata(tmp_path):
    exe_path = touch_exe(tmp_path)
    write_metadata_for_exe(exe_path)
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

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["packaged_dependency_audit"]["forbidden_present"] == []


def test_run_package_smoke_rejects_gui_opencv_distribution(tmp_path):
    exe_path = touch_exe(tmp_path)
    write_metadata_for_exe(exe_path)
    write_dist_info_for_exe(exe_path, "opencv-python-headless")
    write_dist_info_for_exe(exe_path, "opencv-python")
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
    assert report["status"] == "metadata_dependency_mismatch"
    assert "package contains forbidden distribution: opencv-python" in report["error"]
    assert report["packaged_dependency_audit"]["forbidden_present"] == ["opencv-python"]


def test_run_package_smoke_rejects_contrib_opencv_distribution(tmp_path):
    exe_path = touch_exe(tmp_path)
    write_metadata_for_exe(exe_path)
    write_dist_info_for_exe(exe_path, "opencv-contrib-python")
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
    assert report["status"] == "metadata_dependency_mismatch"
    assert (
        "package contains forbidden distribution: opencv-contrib-python"
        in report["error"]
    )
    assert report["packaged_dependency_audit"]["forbidden_present"] == [
        "opencv-contrib-python"
    ]


def test_run_package_smoke_rejects_missing_headless_opencv_metadata(tmp_path):
    exe_path = touch_exe(tmp_path)
    metadata = write_metadata_for_exe(exe_path)
    metadata["dependencies"] = {"opencv-python-headless": "not-installed"}
    metadata_path = exe_path.parent / "_internal" / "checkocr2" / "build_metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
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
    assert report["status"] == "metadata_dependency_mismatch"
    assert (
        "metadata missing required dependency: opencv-python-headless"
        in report["error"]
    )


def test_run_package_smoke_rejects_gui_opencv_metadata(tmp_path):
    exe_path = touch_exe(tmp_path)
    metadata = write_metadata_for_exe(exe_path)
    metadata["dependencies"]["opencv-python"] = "4.10.0.84"
    metadata_path = exe_path.parent / "_internal" / "checkocr2" / "build_metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
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
    assert report["status"] == "metadata_dependency_mismatch"
    assert "metadata contains forbidden dependency: opencv-python" in report["error"]


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
    assert report["ocr_ready_mode"] == "fast"
    assert report["ocr_ready"] is True
    assert report["ocr_ready_status"]["runtime_state"] == "Ready"
    assert package_smoke.PACKAGE_SMOKE_FAST_OCR_ENV not in os.environ
    assert package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV not in os.environ


def test_run_package_smoke_can_require_settings_file_status(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    settings_file = tmp_path / "appdata" / "CheckOCR2" / "settings.json"

    def launch(_path: Path) -> FakeProcess:
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text("{}", encoding="utf-8")
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
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

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        require_settings_file=True,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["settings_file_required"] is True
    assert report["settings_file"] == str(settings_file)


def test_run_package_smoke_can_use_isolated_appdata(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    previous_appdata = os.environ.get("APPDATA")

    def launch(_path: Path) -> FakeProcess:
        appdata_dir = Path(os.environ["APPDATA"])
        assert appdata_dir.name.startswith("checkocr2-package-smoke-appdata-")
        settings_file = appdata_dir / "CheckOCR2" / "settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text("{}", encoding="utf-8")
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
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

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        require_settings_file=True,
        isolated_appdata=True,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["isolated_appdata"] is True
    assert Path(report["settings_file"]).is_relative_to(Path(report["appdata_dir"]))
    assert report["appdata_cleanup"]["removed"] is True
    assert not Path(report["appdata_dir"]).exists()
    assert os.environ.get("APPDATA") == previous_appdata


def test_run_package_smoke_reports_isolated_appdata_cleanup_failure(
    tmp_path, monkeypatch
):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    original_rmtree = package_smoke.shutil.rmtree

    def launch(_path: Path) -> FakeProcess:
        appdata_dir = Path(os.environ["APPDATA"])
        settings_file = appdata_dir / "CheckOCR2" / "settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text("{}", encoding="utf-8")
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
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

    def fail_rmtree(_path: Path) -> None:
        raise OSError("settings file is locked")

    monkeypatch.setattr(package_smoke.shutil, "rmtree", fail_rmtree)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        require_settings_file=True,
        isolated_appdata=True,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "appdata_cleanup_failed"
    assert report["appdata_cleanup"]["removed"] is False
    assert "settings file is locked" in report["appdata_cleanup"]["error"]

    original_rmtree(Path(report["appdata_dir"]), ignore_errors=True)


def test_run_package_smoke_rejects_settings_file_outside_appdata(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    outside_settings_file = tmp_path / "outside" / "settings.json"

    def launch(_path: Path) -> FakeProcess:
        outside_settings_file.parent.mkdir(parents=True)
        outside_settings_file.write_text("{}", encoding="utf-8")
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
            json.dumps(
                {
                    "runtime_state": "Ready",
                    "ocr_ready": True,
                    "settings_file": str(outside_settings_file),
                }
            ),
            encoding="utf-8",
        )
        return process

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        require_settings_file=True,
        isolated_appdata=True,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "settings_file_missing"
    assert "outside the smoke APPDATA directory" in report["error"]
    assert not Path(report["appdata_dir"]).exists()


def test_run_package_smoke_can_use_explicit_appdata_dir(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    appdata_dir = tmp_path / "smoke-appdata"

    def launch(_path: Path) -> FakeProcess:
        assert Path(os.environ["APPDATA"]) == appdata_dir
        settings_file = appdata_dir / "CheckOCR2" / "settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text("{}", encoding="utf-8")
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
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

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        require_settings_file=True,
        appdata_dir=appdata_dir,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert Path(report["appdata_dir"]) == appdata_dir
    assert appdata_dir.exists()


def test_run_package_smoke_resolves_relative_appdata_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    relative_appdata = Path("smoke-appdata")
    expected_appdata = (tmp_path / relative_appdata).resolve()

    def launch(_path: Path) -> FakeProcess:
        assert Path(os.environ["APPDATA"]) == expected_appdata
        settings_file = expected_appdata / "CheckOCR2" / "settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text("{}", encoding="utf-8")
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
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

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        require_settings_file=True,
        appdata_dir=relative_appdata,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert Path(report["appdata_dir"]) == expected_appdata


def test_run_package_smoke_rejects_appdata_conflict(tmp_path):
    exe_path = touch_exe(tmp_path)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        isolated_appdata=True,
        appdata_dir=tmp_path / "appdata",
    )

    assert exit_code == 2
    assert report["error_code"] == "appdata_conflict"


def test_run_package_smoke_preserves_existing_positional_api_shape(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        package_smoke.DEFAULT_TITLE_FRAGMENT,
        60.0,
        0.5,
        5.0,
        False,
        False,
        20.0,
        "fast",
        None,
        None,
        lambda _path: process,
        lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["ocr_ready_required"] is False


def test_run_package_smoke_reports_missing_settings_file_status(tmp_path):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    missing_settings_file = tmp_path / "missing" / "settings.json"

    def launch(_path: Path) -> FakeProcess:
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
            json.dumps(
                {
                    "runtime_state": "Ready",
                    "ocr_ready": True,
                    "settings_file": str(missing_settings_file),
                }
            ),
            encoding="utf-8",
        )
        return process

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        require_settings_file=True,
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 1
    assert report["status"] == "settings_file_missing"
    assert "Reported settings_file does not exist" in report["error"]


def test_run_package_smoke_requires_ocr_ready_for_settings_file_check(tmp_path):
    exe_path = touch_exe(tmp_path)

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_settings_file=True,
    )

    assert exit_code == 2
    assert report["error_code"] == "settings_file_requires_ocr_ready"


def test_run_package_smoke_can_require_real_ocr_ready_status(tmp_path, monkeypatch):
    exe_path = touch_exe(tmp_path)
    process = FakeProcess(pid=100)
    monkeypatch.setenv(package_smoke.PACKAGE_SMOKE_FAST_OCR_ENV, "stale")

    def launch(_path: Path) -> FakeProcess:
        assert package_smoke.PACKAGE_SMOKE_FAST_OCR_ENV not in os.environ
        status_path = Path(os.environ[package_smoke.PACKAGE_SMOKE_STATUS_FILE_ENV])
        status_path.write_text(
            json.dumps({"runtime_state": "Ready", "ocr_ready": True}),
            encoding="utf-8",
        )
        return process

    exit_code, report = package_smoke.run_package_smoke(
        exe_path,
        require_ocr_ready=True,
        ocr_ready_mode="real",
        process_launcher=launch,
        list_windows=lambda: [
            package_smoke.WindowInfo(hwnd=10, pid=100, title="Check Capture OCR V6.1")
        ],
        sleep=lambda _seconds: None,
    )

    assert exit_code == 0
    assert report["status"] == "ok"
    assert report["ocr_ready_required"] is True
    assert report["ocr_ready_mode"] == "real"
    assert report["ocr_ready"] is True
    assert report["ocr_ready_status"]["runtime_state"] == "Ready"
    assert os.environ[package_smoke.PACKAGE_SMOKE_FAST_OCR_ENV] == "stale"
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
    assert report["termination"] == {
        "terminated": True,
        "killed": False,
        "exit_code": 0,
    }
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
    assert report["termination"] == {
        "terminated": False,
        "killed": False,
        "exit_code": 7,
    }
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

    exit_code = package_smoke.main(
        [str(exe_path), "--timeout", "1", "--poll-interval", "0.1"]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"status": "ok", "exe_path": str(exe_path)}
