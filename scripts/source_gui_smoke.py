"""Smoke-test a source CheckOCR2 launcher.

The script launches a Python entrypoint such as ``python check_capture_ocr.py``,
waits for the Tk window title, optionally waits for the GUI Ready status file,
prints a JSON report, and terminates the launched process.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.package_smoke import (  # noqa: E402
    DEFAULT_OCR_READY_MODE,
    DEFAULT_OCR_READY_TIMEOUT_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_TERMINATE_TIMEOUT_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TITLE_FRAGMENT,
    OCR_READY_MODES,
    SmokeProcess,
    SmokeReport,
    TemporarySmokeEnvironment,
    WindowLister,
    iter_window_titles,
    positive_float,
    positive_int,
    remove_appdata_dir,
    terminate_process,
    validate_smoke_settings_file,
    validate_window_size,
    wait_for_ocr_ready,
    wait_for_window,
    window_size_report,
)

SourceProcessLauncher = Callable[[list[str], Path], SmokeProcess]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entrypoint",
        required=True,
        help='Source command to launch, for example "python check_capture_ocr.py"',
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Working directory for the source launcher",
    )
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
        help="Seconds between window-title/status checks",
    )
    parser.add_argument(
        "--terminate-timeout",
        type=positive_float,
        default=DEFAULT_TERMINATE_TIMEOUT_SECONDS,
        help="Seconds to wait after terminating before killing the process",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Set source-smoke OCR status env vars and wait for GUI Ready state",
    )
    parser.add_argument(
        "--require-settings-file",
        action="store_true",
        help="Fail unless Ready status reports an existing settings file. Requires --require-ready.",
    )
    parser.add_argument(
        "--isolated-appdata",
        action="store_true",
        help="Run the source app with a temporary APPDATA directory and remove it after smoke.",
    )
    parser.add_argument(
        "--appdata-dir",
        type=Path,
        help="Run the source app with this APPDATA directory for smoke verification.",
    )
    parser.add_argument(
        "--ocr-ready-timeout",
        type=positive_float,
        default=DEFAULT_OCR_READY_TIMEOUT_SECONDS,
        help="Seconds to wait for source-smoke OCR Ready status",
    )
    parser.add_argument(
        "--ocr-ready-mode",
        choices=OCR_READY_MODES,
        default=DEFAULT_OCR_READY_MODE,
        help="'fast' bypasses model loading; 'real' waits for EasyOCR initialization.",
    )
    parser.add_argument(
        "--min-window-width",
        type=positive_int,
        default=None,
        help="Fail if the main window is narrower than this many pixels",
    )
    parser.add_argument(
        "--min-window-height",
        type=positive_int,
        default=None,
        help="Fail if the main window is shorter than this many pixels",
    )
    return parser.parse_args(argv)


def split_entrypoint(entrypoint: str) -> list[str]:
    parts = shlex.split(entrypoint, posix=os.name != "nt")
    return [part[1:-1] if len(part) >= 2 and part[0] == part[-1] and part[0] in "\"'" else part for part in parts]


def launch_source_entrypoint(command: list[str], cwd: Path) -> SmokeProcess:
    return subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_error_report(
    entrypoint: str,
    cwd: Path,
    title_fragment: str,
    timeout_seconds: float,
    error_code: str,
    error: str,
) -> SmokeReport:
    return {
        "status": "error",
        "error_code": error_code,
        "error": error,
        "entrypoint": entrypoint,
        "cwd": str(cwd),
        "title_fragment": title_fragment,
        "timeout_seconds": timeout_seconds,
    }


def run_source_gui_smoke(
    entrypoint: str,
    *,
    cwd: Path | None = None,
    title_fragment: str = DEFAULT_TITLE_FRAGMENT,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    terminate_timeout_seconds: float = DEFAULT_TERMINATE_TIMEOUT_SECONDS,
    require_ready: bool = False,
    ocr_ready_timeout_seconds: float = DEFAULT_OCR_READY_TIMEOUT_SECONDS,
    ocr_ready_mode: str = DEFAULT_OCR_READY_MODE,
    process_launcher: SourceProcessLauncher = launch_source_entrypoint,
    list_windows: WindowLister = iter_window_titles,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    require_settings_file: bool = False,
    isolated_appdata: bool = False,
    appdata_dir: Path | None = None,
    min_window_width: int | None = None,
    min_window_height: int | None = None,
) -> tuple[int, SmokeReport]:
    cwd = (cwd or Path.cwd()).expanduser().resolve()
    if require_settings_file and not require_ready:
        return 2, build_error_report(
            entrypoint,
            cwd,
            title_fragment,
            timeout_seconds,
            "settings_file_requires_ready",
            "--require-settings-file requires --require-ready",
        )
    if isolated_appdata and appdata_dir is not None:
        return 2, build_error_report(
            entrypoint,
            cwd,
            title_fragment,
            timeout_seconds,
            "appdata_conflict",
            "--isolated-appdata and --appdata-dir cannot be used together",
        )
    if not cwd.is_dir():
        return 2, build_error_report(
            entrypoint,
            cwd,
            title_fragment,
            timeout_seconds,
            "cwd_not_found",
            f"CWD is not a directory: {cwd}",
        )

    try:
        command = split_entrypoint(entrypoint)
    except ValueError as exc:
        return 2, build_error_report(
            entrypoint,
            cwd,
            title_fragment,
            timeout_seconds,
            "entrypoint_parse_failed",
            str(exc),
        )
    if not command:
        return 2, build_error_report(
            entrypoint,
            cwd,
            title_fragment,
            timeout_seconds,
            "entrypoint_empty",
            "Entrypoint command is empty",
        )

    process: SmokeProcess | None = None
    cleanup_appdata_dir: Path | None = None
    start = clock()
    exit_code = 1
    report: SmokeReport = {
        "status": "launching",
        "entrypoint": entrypoint,
        "command": command,
        "cwd": str(cwd),
        "title_fragment": title_fragment,
        "timeout_seconds": timeout_seconds,
        "ocr_ready_required": require_ready,
        "ocr_ready_mode": ocr_ready_mode if require_ready else None,
        "settings_file_required": require_settings_file,
        "isolated_appdata": isolated_appdata,
        "appdata_dir": str(appdata_dir) if appdata_dir is not None else None,
        "min_window_width": min_window_width,
        "min_window_height": min_window_height,
    }

    try:
        with TemporarySmokeEnvironment(
            require_ocr_ready=require_ready,
            ocr_ready_mode=ocr_ready_mode,
            isolated_appdata=isolated_appdata,
            appdata_dir=appdata_dir,
        ) as status_path:
            if appdata_dir is not None or isolated_appdata:
                report["appdata_dir"] = os.environ.get("APPDATA")
            if isolated_appdata and report.get("appdata_dir"):
                cleanup_appdata_dir = Path(str(report["appdata_dir"]))
            process = process_launcher(command, cwd)

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
                    **window_size_report(window),
                }
            )
            exit_code = 0
            window_size_error = validate_window_size(
                window,
                min_window_width=min_window_width,
                min_window_height=min_window_height,
            )
            if window_size_error:
                report.update({"status": "window_size_too_small", "error": window_size_error})
                exit_code = 1
            if require_ready and status_path is not None:
                exit_code = _wait_for_required_ready_status(
                    report,
                    process,
                    status_path,
                    ocr_ready_timeout_seconds=ocr_ready_timeout_seconds,
                    poll_interval_seconds=poll_interval_seconds,
                    sleep=sleep,
                    clock=clock,
                )
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
        if cleanup_appdata_dir is not None:
            cleanup_report = remove_appdata_dir(cleanup_appdata_dir)
            report["appdata_cleanup"] = cleanup_report
            if not cleanup_report["removed"] and exit_code == 0:
                report["status"] = "appdata_cleanup_failed"
                report["error"] = cleanup_report.get("error")
                exit_code = 1

    return exit_code, report


def _wait_for_required_ready_status(
    report: SmokeReport,
    process: SmokeProcess,
    status_path: Path,
    *,
    ocr_ready_timeout_seconds: float,
    poll_interval_seconds: float,
    sleep: Callable[[float], None],
    clock: Callable[[], float],
) -> int:
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
        if report.get("settings_file_required"):
            expected_appdata_dir = (
                Path(str(report["appdata_dir"])) if report.get("appdata_dir") else None
            )
            settings_error = validate_smoke_settings_file(
                smoke_status,
                expected_appdata_dir=expected_appdata_dir,
            )
            if settings_error:
                report.update({"status": "settings_file_missing", "error": settings_error})
                return 1
            report["settings_file"] = smoke_status["settings_file"]
        return 0
    if ready_status == "process_exited":
        report.update(
            {
                "status": "ocr_ready_process_exited",
                "process_exit_code": ready_return_code,
                "error": "Process exited before OCR Ready status was reported",
            }
        )
        return 1
    report.update(
        {
            "status": "ocr_ready_timeout",
            "error": "Timed out waiting for OCR Ready status",
        }
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exit_code, report = run_source_gui_smoke(
        args.entrypoint,
        cwd=args.cwd,
        title_fragment=args.title_fragment,
        timeout_seconds=args.timeout,
        poll_interval_seconds=args.poll_interval,
        terminate_timeout_seconds=args.terminate_timeout,
        require_ready=args.require_ready,
        require_settings_file=args.require_settings_file,
        isolated_appdata=args.isolated_appdata,
        appdata_dir=args.appdata_dir,
        ocr_ready_timeout_seconds=args.ocr_ready_timeout,
        ocr_ready_mode=args.ocr_ready_mode,
        min_window_width=args.min_window_width,
        min_window_height=args.min_window_height,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
