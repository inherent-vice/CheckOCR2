"""Replay copied CouponCheck images through an OCR engine and write run artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checkocr2.excel_io import export_grid_rows, load_grid_rows  # noqa: E402
from checkocr2.image_processing import upscale_image  # noqa: E402
from checkocr2.models import (  # noqa: E402
    CODE_COL,
    DATE_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_DONE,
    STATUS_ERROR_CAPTURE_FAILED,
    STATUS_ERROR_PROCESSING,
)
from checkocr2.ocr_engine import (  # noqa: E402
    create_ocr_reader,
    default_ocr_languages,
    extract_text_with_confidence,
    normalize_ocr_engine,
    read_ocr_text,
)
from checkocr2.ocr_field_analysis import analyze_date_field, analyze_rate_field  # noqa: E402
from checkocr2.ocr_field_extraction import select_field_text_from_ocr_results  # noqa: E402
from checkocr2.ocr_paddle_engine import create_paddleocr_pipeline_reader  # noqa: E402
from checkocr2.paths import updated_workbook_path  # noqa: E402
from checkocr2.run_report import (  # noqa: E402
    create_run_report,
    finalize_run_report,
    record_row_reports,
    report_output_path,
    write_run_report,
)
from scripts.benchmark_ocr import FIELD_ALLOWLISTS  # noqa: E402
from scripts.extract_real_data_ocr_fixtures import (  # noqa: E402
    DEFAULT_DATE_ROI,
    DEFAULT_FULL_609X428_DATE_ROI,
    DEFAULT_FULL_609X428_RATE_ROI,
    DEFAULT_FULL_DATE_ROI,
    DEFAULT_FULL_RATE_ROI,
    DEFAULT_RATE_ROI,
    format_roi,
    layout_for_image,
    parse_roi,
    roi_profile_for_image,
    roi_to_box,
    select_roi_for_field,
    validate_layout,
)

DEFAULT_OUTPUT_DIR = Path(".analysis_tmp/real_data_replay")
DEFAULT_REPORT_NAME = "real_data_replay_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-excel", type=Path, required=True)
    parser.add_argument("--day-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--engine", default="easyocr", type=normalize_ocr_engine)
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--layout", choices=("auto", "cropped", "full"), default="auto")
    parser.add_argument("--date-roi", default=DEFAULT_DATE_ROI)
    parser.add_argument("--rate-roi", default=DEFAULT_RATE_ROI)
    parser.add_argument("--full-date-roi", default=DEFAULT_FULL_DATE_ROI)
    parser.add_argument("--full-rate-roi", default=DEFAULT_FULL_RATE_ROI)
    parser.add_argument(
        "--full-609x428-date-roi",
        default=DEFAULT_FULL_609X428_DATE_ROI,
    )
    parser.add_argument(
        "--full-609x428-rate-roi",
        default=DEFAULT_FULL_609X428_RATE_ROI,
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--detail", type=int, choices=(0, 1), default=0)
    parser.add_argument("--allowlist-mode", choices=("none", "field"), default="none")
    parser.add_argument("--upscale-factor", type=float, default=2.0)
    parser.add_argument("--upscale-method", default="LANCZOS")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--allow-unsafe-output",
        action="store_true",
        help="Allow output outside .analysis_tmp or the system temp directory.",
    )
    return parser.parse_args(argv)


def replay_real_data_ocr_run(
    *,
    input_excel: Path,
    day_dir: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    engine: str = "easyocr",
    gpu: bool = False,
    layout: str = "auto",
    date_roi: str = DEFAULT_DATE_ROI,
    rate_roi: str = DEFAULT_RATE_ROI,
    full_date_roi: str = DEFAULT_FULL_DATE_ROI,
    full_rate_roi: str = DEFAULT_FULL_RATE_ROI,
    full_609x428_date_roi: str = DEFAULT_FULL_609X428_DATE_ROI,
    full_609x428_rate_roi: str = DEFAULT_FULL_609X428_RATE_ROI,
    limit: int = 0,
    detail: int = 0,
    allowlist_mode: str = "none",
    upscale_factor: float = 2.0,
    upscale_method: str = "LANCZOS",
    overwrite: bool = False,
    allow_unsafe_output: bool = False,
    reader: Any | None = None,
) -> dict[str, Any]:
    input_excel = input_excel.resolve()
    day_dir = day_dir.resolve()
    output_dir = output_dir.resolve()
    engine = normalize_ocr_engine(engine)
    validate_inputs(
        input_excel=input_excel,
        day_dir=day_dir,
        output_dir=output_dir,
        allow_unsafe_output=allow_unsafe_output,
    )
    validate_layout(layout)
    if limit < 0:
        raise ValueError("limit must be zero or greater")
    if allowlist_mode not in {"none", "field"}:
        raise ValueError("allowlist_mode must be none or field")

    output_workbook = updated_workbook_path(output_dir, str(input_excel))
    run_report_path = report_output_path(output_dir, str(input_excel))
    summary_path = output_dir / f"{engine}_{DEFAULT_REPORT_NAME}"
    existing = [
        str(path)
        for path in (output_workbook, run_report_path, summary_path)
        if path.exists() and not overwrite
    ]
    if existing:
        raise FileExistsError("replay output already exists: " + ", ".join(existing))

    rows, missing_columns = load_grid_rows(input_excel)
    if limit:
        rows = rows[:limit]
    if not rows:
        raise ValueError("input Excel has no rows")

    image_dir = day_dir / "images"
    roi_by_layout = {
        "cropped": {
            "date": parse_roi(date_roi, "date"),
            "rate": parse_roi(rate_roi, "rate"),
        },
        "full": {
            "date": parse_roi(full_date_roi, "full date"),
            "rate": parse_roi(full_rate_roi, "full rate"),
        },
        "full_609x428": {
            "date": parse_roi(full_609x428_date_roi, "full 609x428 date"),
            "rate": parse_roi(full_609x428_rate_roi, "full 609x428 rate"),
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    ocr_reader = (
        reader
        if reader is not None
        else create_ocr_reader(engine, default_ocr_languages(engine), gpu=gpu)
    )
    rate_reader = None
    report = create_run_report(
        output_dir=str(output_dir),
        input_excel_path=str(input_excel),
        total_items=len(rows),
        save_detail_images=False,
    )
    report["execution_mode"] = "real_data_replay"
    report.setdefault("settings", {}).update(
        {
            "engine": engine,
            "gpu": gpu,
            "layout": layout,
            "detail": detail,
            "allowlist_mode": allowlist_mode,
            "upscale_factor": upscale_factor,
            "upscale_method": upscale_method,
            "day_dir": str(day_dir),
            "roi": {
                layout_name: {field: format_roi(roi) for field, roi in field_rois.items()}
                for layout_name, field_rois in roi_by_layout.items()
            },
        }
    )

    row_timing_by_index: dict[int, dict[str, Any]] = {}
    row_metadata_by_index: dict[int, dict[str, Any]] = {}
    processed_count = 0
    missing_images: list[str] = []
    processing_errors: list[str] = []

    for index, row in enumerate(rows):
        row_started = time.perf_counter()
        code = str(row.get(CODE_COL, "") or "").strip()
        image_path = image_dir / f"{code}.png"
        timing = row_timing_by_index.setdefault(index, {})
        metadata = row_metadata_by_index.setdefault(index, {})
        if not code or not image_path.exists():
            row[DATE_COL] = ""
            row[RATE_COL] = ""
            row[STATUS_COL] = STATUS_ERROR_CAPTURE_FAILED
            missing_images.append(code)
            timing["row_total_ms"] = elapsed_ms(row_started)
            continue

        try:
            image_layout = layout_for_image(image_path, layout)
            roi_profile = roi_profile_for_image(image_path, layout)
            date_roi = select_roi_for_field(
                image_path=image_path,
                field="date",
                roi_profile=roi_profile,
                roi_by_layout=roi_by_layout,
                reader=ocr_reader,
            )
            date_result = replay_field(
                reader=ocr_reader,
                image_path=image_path,
                source_image_path=image_path,
                roi=date_roi,
                field="date",
                detail=detail,
                allowlist_mode=allowlist_mode,
                upscale_factor=upscale_factor,
                upscale_method=upscale_method,
            )
            if engine == "paddle" and rate_reader is None:
                rate_reader = create_paddleocr_pipeline_reader(
                    default_ocr_languages(engine),
                    gpu=gpu,
                )
            rate_roi = select_roi_for_field(
                image_path=image_path,
                field="rate",
                roi_profile=roi_profile,
                roi_by_layout=roi_by_layout,
                reader=rate_reader if rate_reader is not None else ocr_reader,
            )
            rate_result = replay_field(
                reader=rate_reader if rate_reader is not None else ocr_reader,
                image_path=image_path,
                source_image_path=image_path,
                roi=rate_roi,
                field="rate",
                detail=detail,
                allowlist_mode=allowlist_mode,
                upscale_factor=upscale_factor,
                upscale_method=upscale_method,
                use_pipeline_reader=engine == "paddle",
            )
            date_analysis = analyze_date_field(date_result["raw_text"], "date")
            rate_analysis = analyze_rate_field(rate_result["raw_text"], "rate")
            row[DATE_COL] = date_analysis.value
            row[RATE_COL] = rate_analysis.value
            row[STATUS_COL] = STATUS_DONE
            timing.update(
                {
                    "layout": image_layout,
                    "roi_profile": roi_profile,
                    "date_roi": format_roi(date_roi),
                    "rate_roi": format_roi(rate_roi),
                    "date_total_ms": date_result["timing_ms"],
                    "rate_total_ms": rate_result["timing_ms"],
                }
            )
            metadata["ocr_confidence"] = {
                "date": date_result["confidence"],
                "rate": rate_result["confidence"],
            }
            processed_count += 1
        except Exception as exc:
            row[DATE_COL] = ""
            row[RATE_COL] = ""
            row[STATUS_COL] = STATUS_ERROR_PROCESSING
            error_message = f"{code or f'row {index + 1}'}: {exc}"
            processing_errors.append(error_message)
            metadata["error"] = error_message
        finally:
            timing["row_total_ms"] = elapsed_ms(row_started)

    export_started = time.perf_counter()
    export_grid_rows(rows, output_workbook)
    record_row_reports(report, rows, row_timing_by_index, row_metadata_by_index)
    replay_errors = replay_error_messages(
        processed_count=processed_count,
        row_count=len(rows),
        missing_images=missing_images,
        processing_errors=processing_errors,
    )
    finalize_run_report(
        report,
        rows,
        processed_count=processed_count,
        total_items=len(rows),
        stopped=False,
        output_workbook_path=output_workbook,
        export_timing_ms={"export_ms": elapsed_ms(export_started)},
        error="; ".join(replay_errors) if replay_errors else None,
    )
    write_run_report(report, run_report_path)

    accepted = not replay_errors
    summary = {
        "status": "ready" if accepted else "not_ready",
        "accepted": accepted,
        "execution_mode": "real_data_replay",
        "engine": engine,
        "input_excel": str(input_excel),
        "day_dir": str(day_dir),
        "output_dir": str(output_dir),
        "output_workbook": str(output_workbook),
        "run_report": str(run_report_path),
        "row_count": len(rows),
        "processed_count": processed_count,
        "missing_columns": missing_columns,
        "missing_image_count": len(missing_images),
        "missing_images": missing_images[:20],
        "processing_error_count": len(processing_errors),
        "processing_errors": processing_errors[:20],
        "errors": replay_errors,
    }
    write_json_atomic(summary_path, summary)
    summary["summary_json"] = str(summary_path)
    return summary


def replay_error_messages(
    *,
    processed_count: int,
    row_count: int,
    missing_images: list[str],
    processing_errors: list[str],
) -> list[str]:
    errors: list[str] = []
    if processed_count < row_count:
        errors.append(f"processed_count below row_count: {processed_count} < {row_count}")
    if missing_images:
        errors.append(f"missing source images: {len(missing_images)}")
    if processing_errors:
        errors.append(f"row processing errors: {len(processing_errors)}")
    return errors


def replay_field(
    *,
    reader: Any,
    image_path: Path,
    source_image_path: Path | None,
    roi: tuple[float, float, float, float],
    field: str,
    detail: int,
    allowlist_mode: str,
    upscale_factor: float,
    upscale_method: str,
    use_pipeline_reader: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    allowlist = FIELD_ALLOWLISTS.get(field) if allowlist_mode == "field" else None
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    crop = image.crop(roi_to_box(roi, image.width, image.height))
    processed = upscale_image(
        crop,
        enabled=upscale_factor > 1.0,
        factor=upscale_factor,
        method=upscale_method,
    )
    results = read_ocr_text(reader, np.array(processed), detail=detail, allowlist=allowlist)
    if use_pipeline_reader:
        raw_text = select_field_text_from_ocr_results(results, field)
        confidence = None
        if not raw_text:
            raw_text, confidence = extract_text_with_confidence(results, detail)
    else:
        raw_text, confidence = extract_text_with_confidence(results, detail)
    return {
        "raw_text": raw_text,
        "confidence": confidence,
        "timing_ms": elapsed_ms(started),
    }


def validate_inputs(
    *,
    input_excel: Path,
    day_dir: Path,
    output_dir: Path,
    allow_unsafe_output: bool,
) -> None:
    if not input_excel.exists() or not input_excel.is_file():
        raise FileNotFoundError(f"input Excel not found: {input_excel}")
    image_dir = day_dir / "images"
    if not image_dir.exists() or not image_dir.is_dir():
        raise FileNotFoundError(f"image directory not found: {image_dir}")
    if output_dir == image_dir or is_relative_to(output_dir, image_dir):
        raise ValueError("output_dir must not be the source image directory or one of its children")
    allowed_roots = [
        (ROOT / ".analysis_tmp").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    if any(output_dir == allowed or is_relative_to(output_dir, allowed) for allowed in allowed_roots):
        return
    if not allow_unsafe_output:
        raise ValueError(
            "output_dir must be under .analysis_tmp or the system temp directory; "
            "pass --allow-unsafe-output only for deliberate local experiments"
        )


def elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = replay_real_data_ocr_run(
            input_excel=args.input_excel,
            day_dir=args.day_dir,
            output_dir=args.output_dir,
            engine=args.engine,
            gpu=args.gpu,
            layout=args.layout,
            date_roi=args.date_roi,
            rate_roi=args.rate_roi,
            full_date_roi=args.full_date_roi,
            full_rate_roi=args.full_rate_roi,
            full_609x428_date_roi=args.full_609x428_date_roi,
            full_609x428_rate_roi=args.full_609x428_rate_roi,
            limit=args.limit,
            detail=args.detail,
            allowlist_mode=args.allowlist_mode,
            upscale_factor=args.upscale_factor,
            upscale_method=args.upscale_method,
            overwrite=args.overwrite,
            allow_unsafe_output=args.allow_unsafe_output,
        )
    except (
        FileExistsError,
        FileNotFoundError,
        ValueError,
        OSError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.get("accepted") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
