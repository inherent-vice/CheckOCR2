"""Measure CheckOCR2 source or packaged startup timing."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import package_smoke, source_gui_smoke  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrypoint", required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--ocr-ready-timeout", type=float, default=180.0)
    parser.add_argument("--ocr-ready-mode", choices=("fast", "real"), default="real")
    parser.add_argument("--isolated-appdata", action="store_true")
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args(argv)


def is_exe_entrypoint(entrypoint: str) -> bool:
    try:
        parts = shlex.split(entrypoint, posix=False)
    except ValueError:
        parts = [entrypoint]
    if len(parts) != 1:
        return False
    token = parts[0].strip("\"'")
    return token.lower().endswith(".exe")


def run_measurement(args: argparse.Namespace) -> dict[str, Any]:
    runs = []
    for index in range(max(1, args.repeat)):
        if is_exe_entrypoint(args.entrypoint):
            exe_path = Path(args.entrypoint.strip("\"'"))
            exit_code, report = package_smoke.run_package_smoke(
                exe_path,
                timeout_seconds=args.timeout,
                require_package_metadata=True,
                require_ocr_ready=True,
                ocr_ready_timeout_seconds=args.ocr_ready_timeout,
                ocr_ready_mode=args.ocr_ready_mode,
                require_settings_file=True,
                isolated_appdata=args.isolated_appdata,
                min_window_width=1000,
                min_window_height=600,
                require_clean_exit=True,
                paddle_package=True,
            )
        else:
            exit_code, report = source_gui_smoke.run_source_gui_smoke(
                args.entrypoint,
                cwd=ROOT,
                timeout_seconds=args.timeout,
                require_ready=True,
                ocr_ready_timeout_seconds=args.ocr_ready_timeout,
                ocr_ready_mode=args.ocr_ready_mode,
                require_settings_file=True,
                isolated_appdata=args.isolated_appdata,
                min_window_width=1000,
                min_window_height=600,
                require_clean_exit=True,
            )
        runs.append({"index": index + 1, "exit_code": exit_code, "report": report})
    return {
        "status": "ok" if all(run["exit_code"] == 0 for run in runs) else "error",
        "entrypoint": args.entrypoint,
        "repeat": len(runs),
        "runs": runs,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_measurement(args)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
