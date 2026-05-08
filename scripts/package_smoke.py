"""Smoke-test a packaged Check Capture OCR executable.

The script launches the provided EXE, waits for the main Tk window title, emits
a JSON status report to stdout, and then terminates the process it launched.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DEFAULT_TITLE_FRAGMENT = "Check Capture OCR"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_TERMINATE_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    title: str


class SmokeProcess(Protocol):
    pid: int

    def poll(self) -> int | None:
        ...

    def terminate(self) -> None:
        ...

    def kill(self) -> None:
        ...

    def wait(self, timeout: float | None = None) -> int:
        ...


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
    return parser.parse_args(argv)


def iter_window_titles() -> list[WindowInfo]:
    if sys.platform != "win32":
        return []

    from ctypes import wintypes

    user32 = ctypes.windll.user32
    enum_windows_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    user32.EnumWindows.argtypes = [enum_windows_proc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
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
        titles.append(WindowInfo(hwnd=int(hwnd), pid=int(process_id.value), title=title))
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
        if window.pid == process_id and title_fragment_normalized in window.title.casefold():
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
    process_launcher: ProcessLauncher = launch_exe,
    list_windows: WindowLister = iter_window_titles,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[int, dict[str, bool | float | int | str | dict[str, bool | int | str | None] | None]]:
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

    process: SmokeProcess | None = None
    start = clock()
    exit_code = 1
    report: dict[str, bool | float | int | str | dict[str, bool | int | str | None] | None] = {
        "status": "launching",
        "exe_path": str(exe_path),
        "title_fragment": title_fragment,
        "timeout_seconds": timeout_seconds,
    }

    try:
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
            report.update(
                {
                    "status": "ok",
                    "window_title": window.title,
                    "window_pid": window.pid,
                    "window_hwnd": window.hwnd,
                }
            )
            exit_code = 0
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
                report["termination"] = terminate_process(process, terminate_timeout_seconds)
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

    return exit_code, report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exit_code, report = run_package_smoke(
        args.exe_path,
        title_fragment=args.title_fragment,
        timeout_seconds=args.timeout,
        poll_interval_seconds=args.poll_interval,
        terminate_timeout_seconds=args.terminate_timeout,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
