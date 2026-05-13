"""Run a copied-workbook GUI live smoke against a local image simulator.

This script keeps the production network folder untouched. It starts the real
Tk app, opens a local Tk window that behaves like the target CouponCheck screen,
and lets the existing click/paste/screenshot/OCR workflow process the copied
smoke workbook.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL import Image, ImageTk

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_live_smoke_workspace import check_live_smoke_workspace  # noqa: E402
from scripts.extract_real_data_ocr_fixtures import (  # noqa: E402
    DEFAULT_DATE_ROI,
    DEFAULT_RATE_ROI,
    parse_roi,
)

DEFAULT_MANIFEST = Path(".analysis_tmp/live_smoke/live_smoke_manifest.json")
DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_SIMULATOR_X = 20
DEFAULT_SIMULATOR_Y = 20
DEFAULT_APP_X = 940
DEFAULT_APP_Y = 20


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--day-dir", type=Path, required=True)
    parser.add_argument("--engine", choices=("easyocr", "paddle"), default="easyocr")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--date-roi", default=DEFAULT_DATE_ROI)
    parser.add_argument("--rate-roi", default=DEFAULT_RATE_ROI)
    parser.add_argument("--timeout", type=positive_float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--paste-delay", type=nonnegative_float, default=0.2)
    parser.add_argument("--load-delay", type=nonnegative_float, default=0.4)
    parser.add_argument("--simulator-x", type=int, default=DEFAULT_SIMULATOR_X)
    parser.add_argument("--simulator-y", type=int, default=DEFAULT_SIMULATOR_Y)
    parser.add_argument("--app-x", type=int, default=DEFAULT_APP_X)
    parser.add_argument("--app-y", type=int, default=DEFAULT_APP_Y)
    parser.add_argument(
        "--appdata-dir",
        type=Path,
        help="Use this APPDATA directory. Defaults to an ignored temporary folder.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove expected smoke output workbook/report before running.",
    )
    return parser.parse_args(argv)


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def run_live_smoke_with_local_simulator(
    *,
    manifest_path: Path,
    day_dir: Path,
    engine: str = "easyocr",
    date_roi: str = DEFAULT_DATE_ROI,
    rate_roi: str = DEFAULT_RATE_ROI,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    paste_delay: float = 0.2,
    load_delay: float = 0.4,
    simulator_x: int = DEFAULT_SIMULATOR_X,
    simulator_y: int = DEFAULT_SIMULATOR_Y,
    app_x: int = DEFAULT_APP_X,
    app_y: int = DEFAULT_APP_Y,
    appdata_dir: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    day_dir = day_dir.resolve()
    manifest = load_manifest(manifest_path)
    image_dir = day_dir / "images"
    validate_inputs(manifest, image_dir)
    if overwrite:
        remove_expected_outputs(manifest)

    appdata = appdata_dir.resolve() if appdata_dir else default_appdata_dir(engine)
    appdata.mkdir(parents=True, exist_ok=True)

    previous_env = {
        "APPDATA": os.environ.get("APPDATA"),
        "CHECKOCR2_OCR_ENGINE": os.environ.get("CHECKOCR2_OCR_ENGINE"),
        "CHECKOCR2_PADDLE_MODE": os.environ.get("CHECKOCR2_PADDLE_MODE"),
    }
    os.environ["APPDATA"] = str(appdata)
    os.environ["CHECKOCR2_OCR_ENGINE"] = engine
    if engine == "paddle":
        os.environ.setdefault("CHECKOCR2_PADDLE_MODE", "recognition")

    app = None
    simulator = None
    started = time.monotonic()
    try:
        patch_messageboxes()
        from checkocr2.app import CheckCaptureOCRApp

        app = CheckCaptureOCRApp()
        app.geometry(f"1000x760+{app_x}+{app_y}")
        app.update_idletasks()

        rows = list(manifest.get("rows", []))
        codes = [str(row.get("code", "") or "") for row in rows]
        simulator = CouponCheckImageSimulator(
            app,
            image_dir=image_dir,
            codes=codes,
            x=simulator_x,
            y=simulator_y,
        )
        simulator.wait_ready()

        configure_app_for_smoke(
            app,
            manifest,
            simulator,
            date_roi=parse_roi(date_roi, "date"),
            rate_roi=parse_roi(rate_roi, "rate"),
            paste_delay=paste_delay,
            load_delay=load_delay,
        )
        wait_for_ocr_ready(app, timeout_seconds=timeout_seconds)
        drain_app_events(app)
        app.run_ocr_process()
        wait_for_workflow_completion(app, timeout_seconds=timeout_seconds)
        drain_app_events(app)

        live_check = check_live_smoke_workspace(manifest_path, min_processed=len(codes))
        accepted = bool(live_check.get("accepted"))
        return {
            "accepted": accepted,
            "status": "ok" if accepted else "not_ready",
            "execution_mode": "local_gui_simulator",
            "engine": engine,
            "manifest": str(manifest_path),
            "day_dir": str(day_dir),
            "image_dir": str(image_dir),
            "appdata_dir": str(appdata),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "live_smoke_check": live_check,
        }
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
        restore_env(previous_env)


class CouponCheckImageSimulator:
    def __init__(
        self,
        master,
        *,
        image_dir: Path,
        codes: Sequence[str],
        x: int,
        y: int,
    ) -> None:
        import tkinter as tk

        self.image_dir = image_dir
        self.codes = list(codes)
        self.window = tk.Toplevel(master)
        self.window.title("CheckOCR2 Local CouponCheck Simulator")
        self.code_var = tk.StringVar()
        self.entry = tk.Entry(self.window, textvariable=self.code_var, width=32)
        self.entry.pack(fill="x")
        self.image_label = tk.Label(self.window, borderwidth=0, highlightthickness=0)
        self.image_label.pack()
        self._photo = None
        self._last_code = ""
        self.code_var.trace_add("write", lambda *_args: self.window.after(20, self.sync_image))
        self.window.geometry(f"+{x}+{y}")
        self.window.attributes("-topmost", True)
        self.load_image(self.codes[0] if self.codes else "")
        self.window.update_idletasks()
        self.entry.focus_force()

    def wait_ready(self) -> None:
        self.window.update_idletasks()
        self.window.update()

    @property
    def click_point(self) -> tuple[int, int]:
        return (
            self.entry.winfo_rootx() + max(5, self.entry.winfo_width() // 2),
            self.entry.winfo_rooty() + max(5, self.entry.winfo_height() // 2),
        )

    @property
    def image_origin(self) -> tuple[int, int]:
        return self.image_label.winfo_rootx(), self.image_label.winfo_rooty()

    @property
    def image_size(self) -> tuple[int, int]:
        return self._image_size

    @property
    def full_area(self) -> tuple[int, int, int, int]:
        x, y = self.image_origin
        width, height = self.image_size
        return x, y, x + width, y + height

    def sync_image(self) -> None:
        code = self.code_var.get().strip()
        if code and code != self._last_code:
            self.load_image(code)

    def load_image(self, code: str) -> None:
        self._last_code = code
        image_path = self.image_dir / f"{code}.png"
        if image_path.exists():
            image = Image.open(image_path).convert("RGB")
        else:
            image = Image.new("RGB", (884, 496), "white")
        self._image_size = image.size
        self._photo = ImageTk.PhotoImage(image)
        self.image_label.configure(image=self._photo)
        self.window.update_idletasks()


def configure_app_for_smoke(
    app: Any,
    manifest: dict[str, Any],
    simulator: CouponCheckImageSimulator,
    *,
    date_roi: tuple[float, float, float, float],
    rate_roi: tuple[float, float, float, float],
    paste_delay: float,
    load_delay: float,
) -> None:
    app.input_excel_path.set(str(manifest["smoke_input"]))
    app.output_folder_path.set(str(manifest["output_dir"]))
    app.load_excel_to_grid()
    app.save_detail_images.set(False)
    app.paste_delay.set(paste_delay)
    app.loading_delay.set(load_delay)
    app.click_x.set(simulator.click_point[0])
    app.click_y.set(simulator.click_point[1])
    set_area_vars(
        app,
        "allarea",
        simulator.full_area,
    )
    set_area_vars(
        app,
        "datearea",
        roi_to_screen_box(simulator.image_origin, simulator.image_size, date_roi),
    )
    set_area_vars(
        app,
        "ratearea",
        roi_to_screen_box(simulator.image_origin, simulator.image_size, rate_roi),
    )
    app.update_idletasks()


def set_area_vars(app: Any, prefix: str, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    getattr(app, f"{prefix}_x1").set(x1)
    getattr(app, f"{prefix}_y1").set(y1)
    getattr(app, f"{prefix}_x2").set(x2)
    getattr(app, f"{prefix}_y2").set(y2)


def roi_to_screen_box(
    origin: tuple[int, int],
    size: tuple[int, int],
    roi: tuple[float, float, float, float],
) -> tuple[int, int, int, int]:
    x, y = origin
    width, height = size
    left, top, right, bottom = roi
    return (
        x + int(round(width * left)),
        y + int(round(height * top)),
        x + int(round(width * right)),
        y + int(round(height * bottom)),
    )


def wait_for_ocr_ready(app: Any, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.update()
        if (
            app.ocr_workflow_manager.ocr_reader is not None
            and runtime_state_value(app) == "Ready"
        ):
            return
        if str(getattr(app, "runtime_state", "")).endswith("ERROR"):
            raise RuntimeError("OCR initialization entered Error state")
        time.sleep(0.05)
    raise TimeoutError("Timed out waiting for OCR reader initialization")


def runtime_state_value(app: Any) -> str:
    state = getattr(app, "runtime_state", "")
    return str(getattr(state, "value", state))


def wait_for_workflow_completion(app: Any, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    start_deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        app.update()
        worker = getattr(app, "worker_thread", None)
        if worker is None and time.monotonic() > start_deadline:
            raise RuntimeError("OCR workflow did not start")
        if worker is not None and not worker_is_alive(worker):
            drain_app_events(app)
            return
        time.sleep(0.05)
    raise TimeoutError("Timed out waiting for OCR workflow completion")


def worker_is_alive(worker: Any) -> bool:
    is_alive = getattr(worker, "is_alive", None)
    if callable(is_alive):
        return bool(is_alive())
    return bool(is_alive)


def drain_app_events(app: Any, iterations: int = 20) -> None:
    for _ in range(iterations):
        app.update()
        time.sleep(0.02)


def patch_messageboxes() -> None:
    from tkinter import messagebox

    def no_dialog(*_args: Any, **_kwargs: Any) -> bool:
        return True

    messagebox.showinfo = no_dialog
    messagebox.showwarning = no_dialog
    messagebox.showerror = no_dialog
    messagebox.askyesno = no_dialog


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def validate_inputs(manifest: dict[str, Any], image_dir: Path) -> None:
    for key in ("smoke_input", "output_dir", "expected_output_workbook", "expected_run_report"):
        if not manifest.get(key):
            raise ValueError(f"manifest missing {key}")
    validate_expected_output_paths(manifest)
    if not image_dir.is_dir():
        raise FileNotFoundError(f"image directory not found: {image_dir}")
    missing_images = [
        str(row.get("code", "") or "")
        for row in list(manifest.get("rows", []))
        if not (image_dir / f"{row.get('code', '')}.png").is_file()
    ]
    if missing_images:
        raise FileNotFoundError("missing simulator images: " + ", ".join(missing_images[:5]))


def validate_expected_output_paths(manifest: dict[str, Any]) -> None:
    output_dir = Path(str(manifest["output_dir"])).resolve()
    protected_paths = {
        Path(str(manifest["smoke_input"])).resolve(),
    }
    if manifest.get("source_excel"):
        protected_paths.add(Path(str(manifest["source_excel"])).resolve())

    for key in ("expected_output_workbook", "expected_run_report"):
        path = Path(str(manifest[key])).resolve()
        try:
            path.relative_to(output_dir)
        except ValueError as exc:
            raise ValueError(f"{key} must be under output_dir: {path}") from exc
        if path in protected_paths:
            raise ValueError(f"{key} must not target source or smoke input workbook: {path}")


def remove_expected_outputs(manifest: dict[str, Any]) -> None:
    validate_expected_output_paths(manifest)
    for key in ("expected_output_workbook", "expected_run_report"):
        path = Path(str(manifest[key])).resolve()
        if path.exists():
            path.unlink()


def default_appdata_dir(engine: str) -> Path:
    return (ROOT / ".analysis_tmp" / "live_smoke" / f"appdata_{engine}").resolve()


def restore_env(previous_env: dict[str, str | None]) -> None:
    for key, value in previous_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def write_or_print_report(report: dict[str, Any], output_json: Path | None) -> None:
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if output_json is None:
        print(output)
        return
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(output + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run_live_smoke_with_local_simulator(
            manifest_path=args.manifest,
            day_dir=args.day_dir,
            engine=args.engine,
            date_roi=args.date_roi,
            rate_roi=args.rate_roi,
            timeout_seconds=args.timeout,
            paste_delay=args.paste_delay,
            load_delay=args.load_delay,
            simulator_x=args.simulator_x,
            simulator_y=args.simulator_y,
            app_x=args.app_x,
            app_y=args.app_y,
            appdata_dir=args.appdata_dir,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, TimeoutError, RuntimeError, ValueError, OSError) as exc:
        report = {
            "accepted": False,
            "status": "error",
            "error": str(exc),
            "execution_mode": "local_gui_simulator",
        }
        write_or_print_report(report, args.output_json)
        return 2
    write_or_print_report(report, args.output_json)
    return 0 if report.get("accepted") else 2


if __name__ == "__main__":
    raise SystemExit(main())
