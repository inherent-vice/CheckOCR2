"""Smoke-test a packaged Check Capture OCR executable.

The script launches the provided EXE, waits for the main Tk window title, emits
a JSON status report to stdout, reads packaged build metadata when present, and
then terminates the process it launched.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

DEFAULT_TITLE_FRAGMENT = "Check Capture OCR"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_TERMINATE_TIMEOUT_SECONDS = 5.0
DEFAULT_OCR_READY_TIMEOUT_SECONDS = 20.0
DEFAULT_OCR_READY_MODE = "fast"
OCR_READY_MODES = ("fast", "real")
PACKAGE_SMOKE_FAST_OCR_ENV = "CHECKOCR2_PACKAGE_SMOKE_FAST_OCR"
PACKAGE_SMOKE_STATUS_FILE_ENV = "CHECKOCR2_PACKAGE_SMOKE_STATUS_FILE"
REQUIRED_METADATA_DISTRIBUTIONS = ("opencv-python-headless",)
FORBIDDEN_PACKAGED_DISTRIBUTIONS = ("opencv-python", "opencv-contrib-python")
SmokeReport = dict[str, Any]


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    title: str


class SmokeProcess(Protocol):
    pid: int

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


WindowLister = Callable[[], Iterable[WindowInfo]]
ProcessLauncher = Callable[[Path], SmokeProcess]


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe_path", type=Path, help="Path to CheckCaptureOCR_V6.1.exe")
    parser.add_argument(
        "--title-fragment",
        default=DEFAULT_TITLE_FRAGMENT,
        help="Window title fragment that marks a successful launch",
    )
    parser.add_argument(
        "--timeout",
        type=positive_float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Seconds to wait for the window title",
    )
    parser.add_argument(
        "--poll-interval",
        type=positive_float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Seconds between window-title checks",
    )
    parser.add_argument(
        "--terminate-timeout",
        type=positive_float,
        default=DEFAULT_TERMINATE_TIMEOUT_SECONDS,
        help="Seconds to wait after terminating before killing the process",
    )
    parser.add_argument(
        "--require-package-metadata",
        action="store_true",
        help="Fail unless packaged build_metadata.json is present and readable",
    )
    parser.add_argument(
        "--require-ocr-ready",
        action="store_true",
        help="Run in explicit package-smoke OCR mode and wait for GUI Ready state",
    )
    parser.add_argument(
        "--require-settings-file",
        action="store_true",
        help="Fail unless OCR-ready status reports an existing settings file. Requires --require-ocr-ready.",
    )
    parser.add_argument(
        "--isolated-appdata",
        action="store_true",
        help="Run the packaged app with a temporary APPDATA directory and remove it after smoke.",
    )
    parser.add_argument(
        "--appdata-dir",
        type=Path,
        help="Run the packaged app with this APPDATA directory for smoke verification.",
    )
    parser.add_argument(
        "--ocr-ready-timeout",
        type=positive_float,
        default=DEFAULT_OCR_READY_TIMEOUT_SECONDS,
        help="Seconds to wait for package-smoke OCR Ready status",
    )
    parser.add_argument(
        "--ocr-ready-mode",
        choices=OCR_READY_MODES,
        default=DEFAULT_OCR_READY_MODE,
        help=(
            "OCR Ready validation mode. 'fast' bypasses model loading for "
            "startup smoke; 'real' waits for packaged EasyOCR initialization."
        ),
    )
    parser.add_argument(
        "--max-package-size-mb",
        type=positive_float,
        default=None,
        help="Fail if the packaged directory is larger than this size in MB",
    )
    parser.add_argument(
        "--max-startup-seconds",
        type=positive_float,
        default=None,
        help="Fail if the main window takes longer than this many seconds to appear",
    )
    return parser.parse_args(argv)


def iter_window_titles() -> list[WindowInfo]:
    if sys.platform != "win32":
        return []

    from ctypes import wintypes

    user32 = ctypes.windll.user32
    enum_windows_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )

    user32.EnumWindows.argtypes = [enum_windows_proc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD

    titles: list[WindowInfo] = []

    @enum_windows_proc
    def collect_window(hwnd: int, _lparam: int) -> int:
        if not user32.IsWindowVisible(hwnd):
            return 1

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return 1

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return 1

        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        titles.append(
            WindowInfo(hwnd=int(hwnd), pid=int(process_id.value), title=title)
        )
        return 1

    user32.EnumWindows(collect_window, 0)
    return titles


def find_matching_window(
    title_fragment: str,
    process_id: int,
    list_windows: WindowLister = iter_window_titles,
) -> WindowInfo | None:
    title_fragment_normalized = title_fragment.casefold()
    for window in list_windows():
        if (
            window.pid == process_id
            and title_fragment_normalized in window.title.casefold()
        ):
            return window
    return None


def wait_for_window(
    process: SmokeProcess,
    title_fragment: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
    list_windows: WindowLister = iter_window_titles,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[str, WindowInfo | None, int | None]:
    deadline = clock() + timeout_seconds
    while True:
        match = find_matching_window(title_fragment, process.pid, list_windows)
        if match is not None:
            return "ok", match, None

        return_code = process.poll()
        if return_code is not None:
            return "process_exited", None, return_code

        now = clock()
        if now >= deadline:
            return "timeout", None, None

        sleep(min(poll_interval_seconds, deadline - now))


def wait_for_ocr_ready(
    process: SmokeProcess,
    status_path: Path,
    timeout_seconds: float,
    poll_interval_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[str, dict[str, Any] | None, int | None]:
    deadline = clock() + timeout_seconds
    last_status: dict[str, Any] | None = None
    while True:
        if status_path.is_file():
            try:
                last_status = json.loads(status_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                last_status = None
            if (
                last_status
                and last_status.get("runtime_state") == "Ready"
                and last_status.get("ocr_ready") is True
            ):
                return "ok", last_status, None

        return_code = process.poll()
        if return_code is not None:
            return "process_exited", last_status, return_code

        now = clock()
        if now >= deadline:
            return "timeout", last_status, None

        sleep(min(poll_interval_seconds, deadline - now))


def launch_exe(exe_path: Path) -> SmokeProcess:
    return subprocess.Popen(
        [str(exe_path)],
        cwd=str(exe_path.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def terminate_process(
    process: SmokeProcess,
    terminate_timeout_seconds: float,
) -> dict[str, bool | int | str | None]:
    existing_return_code = process.poll()
    if existing_return_code is not None:
        return {
            "terminated": False,
            "killed": False,
            "exit_code": existing_return_code,
        }

    process.terminate()
    try:
        exit_code = process.wait(timeout=terminate_timeout_seconds)
        return {
            "terminated": True,
            "killed": False,
            "exit_code": exit_code,
        }
    except subprocess.TimeoutExpired:
        process.kill()
        exit_code = process.wait(timeout=terminate_timeout_seconds)
        return {
            "terminated": True,
            "killed": True,
            "exit_code": exit_code,
        }


def build_error_report(
    exe_path: Path,
    title_fragment: str,
    timeout_seconds: float,
    error_code: str,
    error: str,
) -> dict[str, bool | float | int | str | None]:
    return {
        "status": "error",
        "error_code": error_code,
        "error": error,
        "exe_path": str(exe_path),
        "title_fragment": title_fragment,
        "timeout_seconds": timeout_seconds,
    }


def run_package_smoke(
    exe_path: Path,
    title_fragment: str = DEFAULT_TITLE_FRAGMENT,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    terminate_timeout_seconds: float = DEFAULT_TERMINATE_TIMEOUT_SECONDS,
    require_package_metadata: bool = False,
    require_ocr_ready: bool = False,
    ocr_ready_timeout_seconds: float = DEFAULT_OCR_READY_TIMEOUT_SECONDS,
    ocr_ready_mode: str = DEFAULT_OCR_READY_MODE,
    max_package_size_mb: float | None = None,
    max_startup_seconds: float | None = None,
    process_launcher: ProcessLauncher = launch_exe,
    list_windows: WindowLister = iter_window_titles,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    *,
    require_settings_file: bool = False,
    isolated_appdata: bool = False,
    appdata_dir: Path | None = None,
) -> tuple[int, SmokeReport]:
    exe_path = exe_path.expanduser()
    if not exe_path.exists():
        report = build_error_report(
            exe_path,
            title_fragment,
            timeout_seconds,
            "exe_not_found",
            f"EXE not found: {exe_path}",
        )
        return 2, report
    if not exe_path.is_file():
        report = build_error_report(
            exe_path,
            title_fragment,
            timeout_seconds,
            "exe_not_file",
            f"EXE path is not a file: {exe_path}",
        )
        return 2, report
    if require_settings_file and not require_ocr_ready:
        report = build_error_report(
            exe_path,
            title_fragment,
            timeout_seconds,
            "settings_file_requires_ocr_ready",
            "--require-settings-file requires --require-ocr-ready",
        )
        return 2, report
    if isolated_appdata and appdata_dir is not None:
        report = build_error_report(
            exe_path,
            title_fragment,
            timeout_seconds,
            "appdata_conflict",
            "--isolated-appdata and --appdata-dir cannot be used together",
        )
        return 2, report

    process: SmokeProcess | None = None
    cleanup_appdata_dir: Path | None = None
    start = clock()
    exit_code = 1
    report: SmokeReport = {
        "status": "launching",
        "exe_path": str(exe_path),
        "title_fragment": title_fragment,
        "timeout_seconds": timeout_seconds,
        "package_size_mb": round(
            directory_size_bytes(exe_path.parent) / (1024 * 1024), 3
        ),
        "max_package_size_mb": max_package_size_mb,
        "max_startup_seconds": max_startup_seconds,
        "ocr_ready_required": require_ocr_ready,
        "ocr_ready_mode": ocr_ready_mode if require_ocr_ready else None,
        "settings_file_required": require_settings_file,
        "isolated_appdata": isolated_appdata,
        "appdata_dir": str(appdata_dir) if appdata_dir is not None else None,
    }
    status_path: Path | None = None

    try:
        with TemporarySmokeEnvironment(
            require_ocr_ready=require_ocr_ready,
            ocr_ready_mode=ocr_ready_mode,
            isolated_appdata=isolated_appdata,
            appdata_dir=appdata_dir,
        ) as status_path:
            if appdata_dir is not None or isolated_appdata:
                report["appdata_dir"] = os.environ.get("APPDATA")
            if isolated_appdata and report.get("appdata_dir"):
                cleanup_appdata_dir = Path(str(report["appdata_dir"]))
            process = process_launcher(exe_path)
        report["pid"] = process.pid
        wait_status, window, process_return_code = wait_for_window(
            process,
            title_fragment,
            timeout_seconds,
            poll_interval_seconds,
            list_windows=list_windows,
            sleep=sleep,
            clock=clock,
        )
        report["elapsed_seconds"] = round(clock() - start, 3)

        if wait_status == "ok" and window is not None:
            package_metadata = read_packaged_metadata(exe_path)
            packaged_dependency_audit = audit_packaged_distributions(exe_path)
            report.update(
                {
                    "status": "ok",
                    "window_title": window.title,
                    "window_pid": window.pid,
                    "window_hwnd": window.hwnd,
                    "package_metadata": package_metadata,
                    "packaged_dependency_audit": packaged_dependency_audit,
                }
            )
            exit_code = 0
            if require_package_metadata and package_metadata is None:
                report.update(
                    {
                        "status": "metadata_missing",
                        "error": "Packaged build_metadata.json was not found",
                    }
                )
                exit_code = 1
            elif require_package_metadata:
                dependency_errors = validate_packaged_dependencies(
                    package_metadata,
                    packaged_dependency_audit,
                )
                if dependency_errors:
                    report.update(
                        {
                            "status": "metadata_dependency_mismatch",
                            "error": "; ".join(dependency_errors),
                        }
                    )
                    exit_code = 1
            if (
                max_package_size_mb is not None
                and float(report["package_size_mb"]) > max_package_size_mb
                and exit_code == 0
            ):
                report.update(
                    {
                        "status": "package_size_exceeded",
                        "error": (
                            f"Package size {report['package_size_mb']} MB exceeds "
                            f"budget {max_package_size_mb} MB"
                        ),
                    }
                )
                exit_code = 1
            if (
                max_startup_seconds is not None
                and float(report["elapsed_seconds"]) > max_startup_seconds
                and exit_code == 0
            ):
                report.update(
                    {
                        "status": "startup_time_exceeded",
                        "error": (
                            f"Startup time {report['elapsed_seconds']} seconds exceeds "
                            f"budget {max_startup_seconds} seconds"
                        ),
                    }
                )
                exit_code = 1
            if require_ocr_ready and status_path is not None and exit_code == 0:
                ready_status, smoke_status, ready_return_code = wait_for_ocr_ready(
                    process,
                    status_path,
                    ocr_ready_timeout_seconds,
                    poll_interval_seconds,
                    sleep=sleep,
                    clock=clock,
                )
                report["ocr_ready_status"] = smoke_status
                if ready_status == "ok" and smoke_status is not None:
                    report["ocr_ready"] = True
                    if require_settings_file:
                        expected_appdata_dir = (
                            Path(str(report["appdata_dir"]))
                            if report.get("appdata_dir")
                            else None
                        )
                        settings_error = validate_smoke_settings_file(
                            smoke_status,
                            expected_appdata_dir=expected_appdata_dir,
                        )
                        if settings_error:
                            report.update(
                                {
                                    "status": "settings_file_missing",
                                    "error": settings_error,
                                }
                            )
                            exit_code = 1
                        else:
                            report["settings_file"] = smoke_status["settings_file"]
                elif ready_status == "process_exited":
                    report.update(
                        {
                            "status": "ocr_ready_process_exited",
                            "process_exit_code": ready_return_code,
                            "error": "Process exited before OCR Ready status was reported",
                        }
                    )
                    exit_code = 1
                else:
                    report.update(
                        {
                            "status": "ocr_ready_timeout",
                            "error": "Timed out waiting for OCR Ready status",
                        }
                    )
                    exit_code = 1
        elif wait_status == "process_exited":
            report.update(
                {
                    "status": "process_exited",
                    "process_exit_code": process_return_code,
                    "error": "Process exited before a matching window appeared",
                }
            )
        else:
            report.update(
                {
                    "status": "timeout",
                    "error": "Timed out waiting for a matching window title",
                }
            )
    except OSError as exc:
        report.update(
            {
                "status": "error",
                "error_code": "launch_failed",
                "error": str(exc),
                "elapsed_seconds": round(clock() - start, 3),
            }
        )
        exit_code = 2
    finally:
        if process is not None:
            try:
                report["termination"] = terminate_process(
                    process, terminate_timeout_seconds
                )
            except OSError as exc:
                report["termination"] = {
                    "terminated": False,
                    "killed": False,
                    "exit_code": None,
                    "error": str(exc),
                }
                if exit_code == 0:
                    report["status"] = "termination_failed"
                    exit_code = 1
        if cleanup_appdata_dir is not None:
            cleanup_report = remove_appdata_dir(cleanup_appdata_dir)
            report["appdata_cleanup"] = cleanup_report
            if not cleanup_report["removed"] and exit_code == 0:
                report["status"] = "appdata_cleanup_failed"
                report["error"] = cleanup_report.get("error")
                exit_code = 1

    return exit_code, report


def remove_appdata_dir(appdata_dir: Path) -> dict[str, bool | str]:
    report: dict[str, bool | str] = {
        "path": str(appdata_dir),
        "required": True,
        "removed": False,
    }
    try:
        if appdata_dir.exists():
            shutil.rmtree(appdata_dir)
        report["removed"] = not appdata_dir.exists()
    except OSError as exc:
        report["error"] = str(exc)
    return report


def validate_smoke_settings_file(
    smoke_status: dict[str, Any],
    *,
    expected_appdata_dir: Path | None = None,
) -> str | None:
    settings_file = smoke_status.get("settings_file")
    if not settings_file:
        return "OCR Ready status did not report settings_file"
    settings_path = Path(str(settings_file))
    if not settings_path.is_file():
        return f"Reported settings_file does not exist: {settings_file}"
    if expected_appdata_dir is not None:
        try:
            settings_path.resolve().relative_to(expected_appdata_dir.resolve())
        except ValueError:
            return (
                "Reported settings_file is outside the smoke APPDATA directory: "
                f"{settings_file}"
            )
    return None


def read_packaged_metadata(exe_path: Path) -> dict[str, object] | None:
    candidates = [
        exe_path.parent / "_internal" / "checkocr2" / "build_metadata.json",
        exe_path.parent / "checkocr2" / "build_metadata.json",
        exe_path.parent / "build_metadata.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return None


def audit_packaged_distributions(exe_path: Path) -> dict[str, object]:
    package_root = packaged_internal_root(exe_path)
    distributions = package_distributions(package_root)
    distribution_names = set(distributions)
    forbidden_present = sorted(
        name for name in FORBIDDEN_PACKAGED_DISTRIBUTIONS if name in distribution_names
    )
    return {
        "root": str(package_root),
        "distributions": distributions,
        "forbidden_present": forbidden_present,
    }


def packaged_internal_root(exe_path: Path) -> Path:
    internal_root = exe_path.parent / "_internal"
    if internal_root.is_dir():
        return internal_root
    return exe_path.parent


def package_distributions(package_root: Path) -> dict[str, str]:
    distributions: dict[str, str] = {}
    for dist_info_dir in sorted(package_root.glob("*.dist-info")):
        if not dist_info_dir.is_dir():
            continue
        distribution_name, distribution_version = read_distribution_metadata(
            dist_info_dir
        )
        distributions[normalize_distribution_name(distribution_name)] = (
            distribution_version
        )
    return distributions


def read_distribution_metadata(dist_info_dir: Path) -> tuple[str, str]:
    metadata_path = dist_info_dir / "METADATA"
    distribution_name: str | None = None
    distribution_version: str | None = None
    try:
        for line in metadata_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            key, separator, value = line.partition(":")
            if not separator:
                continue
            normalized_key = key.casefold()
            if normalized_key == "name":
                distribution_name = value.strip()
            elif normalized_key == "version":
                distribution_version = value.strip()
            if distribution_name and distribution_version:
                break
    except OSError:
        distribution_name = None
        distribution_version = None

    fallback_name, fallback_version = parse_dist_info_dir_name(dist_info_dir.name)
    return distribution_name or fallback_name, distribution_version or fallback_version


def parse_dist_info_dir_name(directory_name: str) -> tuple[str, str]:
    stem = directory_name.removesuffix(".dist-info")
    name, separator, version = stem.rpartition("-")
    if not separator:
        return stem, "unknown"
    return name, version


def normalize_distribution_name(distribution_name: str) -> str:
    return distribution_name.replace("_", "-").casefold()


def validate_packaged_dependencies(
    package_metadata: dict[str, object],
    packaged_dependency_audit: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    dependencies = package_metadata.get("dependencies", {})
    if not isinstance(dependencies, dict):
        errors.append("build metadata dependencies must be an object")
        dependencies = {}

    for required_name in REQUIRED_METADATA_DISTRIBUTIONS:
        version = dependencies.get(required_name)
        if not isinstance(version, str) or not version or version == "not-installed":
            errors.append(f"metadata missing required dependency: {required_name}")

    for forbidden_name in FORBIDDEN_PACKAGED_DISTRIBUTIONS:
        version = dependencies.get(forbidden_name)
        if isinstance(version, str) and version and version != "not-installed":
            errors.append(f"metadata contains forbidden dependency: {forbidden_name}")

    for forbidden_name in packaged_dependency_audit.get("forbidden_present", []):
        errors.append(f"package contains forbidden distribution: {forbidden_name}")

    return errors


def directory_size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def smoke_status_path() -> Path:
    return (
        Path(tempfile.gettempdir()) / f"checkocr2-package-smoke-{uuid.uuid4().hex}.json"
    )


class TemporarySmokeEnvironment:
    def __init__(
        self,
        *,
        require_ocr_ready: bool,
        ocr_ready_mode: str = DEFAULT_OCR_READY_MODE,
        isolated_appdata: bool = False,
        appdata_dir: Path | None = None,
    ):
        self.require_ocr_ready = require_ocr_ready
        self.ocr_ready_mode = ocr_ready_mode
        self.isolated_appdata = isolated_appdata
        self.appdata_dir = appdata_dir
        self.status_path = smoke_status_path() if require_ocr_ready else None
        self.temporary_appdata_dir: Path | None = None
        self.previous: dict[str, str | None] = {}

    def __enter__(self) -> Path | None:
        updates: dict[str, str | None] = {}
        if self.require_ocr_ready and self.status_path is not None:
            updates[PACKAGE_SMOKE_STATUS_FILE_ENV] = str(self.status_path)
            if self.ocr_ready_mode == "fast":
                updates[PACKAGE_SMOKE_FAST_OCR_ENV] = "1"
            else:
                updates[PACKAGE_SMOKE_FAST_OCR_ENV] = None
        if self.isolated_appdata:
            self.temporary_appdata_dir = Path(
                tempfile.mkdtemp(prefix="checkocr2-package-smoke-appdata-")
            )
            updates["APPDATA"] = str(self.temporary_appdata_dir)
        elif self.appdata_dir is not None:
            self.appdata_dir = self.appdata_dir.expanduser().resolve()
            self.appdata_dir.mkdir(parents=True, exist_ok=True)
            updates["APPDATA"] = str(self.appdata_dir)
        for key, value in updates.items():
            self.previous[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return self.status_path

    def __exit__(self, *_exc_info: object) -> None:
        for key, previous_value in self.previous.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exit_code, report = run_package_smoke(
        args.exe_path,
        title_fragment=args.title_fragment,
        timeout_seconds=args.timeout,
        poll_interval_seconds=args.poll_interval,
        terminate_timeout_seconds=args.terminate_timeout,
        require_package_metadata=args.require_package_metadata,
        require_ocr_ready=args.require_ocr_ready,
        ocr_ready_timeout_seconds=args.ocr_ready_timeout,
        ocr_ready_mode=args.ocr_ready_mode,
        max_package_size_mb=args.max_package_size_mb,
        max_startup_seconds=args.max_startup_seconds,
        require_settings_file=args.require_settings_file,
        isolated_appdata=args.isolated_appdata,
        appdata_dir=args.appdata_dir,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
