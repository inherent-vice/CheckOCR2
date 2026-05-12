"""Workflow run setup helpers for the legacy Tk OCR manager."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .run_report import create_run_report, report_output_path


@dataclass(frozen=True)
class WorkflowRunSetup:
    paste_delay: float
    load_delay: float
    coords: dict[str, Any]
    input_excel_file: str
    save_folder: str
    report_path: Path
    report: dict[str, Any]


def prepare_workflow_run(
    ui_settings: Mapping[str, Any],
    output_dir: str,
    input_excel_file: str,
    total_items: int,
    save_detail_images: bool,
    *,
    makedirs: Callable[..., object] = os.makedirs,
) -> WorkflowRunSetup:
    """Prepare stable per-run paths, delays, coordinates, and report metadata."""

    paste_delay = ui_settings["delays"]["paste"]
    load_delay = ui_settings["delays"]["loading"]
    coords = {
        "click": ui_settings["click_point"],
        "all": ui_settings["all_area"],
        "date": ui_settings["date_area"],
        "rate": ui_settings["rate_area"],
    }

    if input_excel_file:
        base_name = os.path.splitext(os.path.basename(input_excel_file))[0]
        save_folder = os.path.join(output_dir, base_name)
    else:
        save_folder = os.path.join(output_dir, "ocr_images")

    makedirs(save_folder, exist_ok=True)
    report_path = report_output_path(output_dir, input_excel_file)
    report = create_run_report(
        output_dir=output_dir,
        input_excel_path=input_excel_file or "",
        total_items=total_items,
        save_detail_images=save_detail_images,
    )

    return WorkflowRunSetup(
        paste_delay=paste_delay,
        load_delay=load_delay,
        coords=coords,
        input_excel_file=input_excel_file,
        save_folder=save_folder,
        report_path=report_path,
        report=report,
    )
