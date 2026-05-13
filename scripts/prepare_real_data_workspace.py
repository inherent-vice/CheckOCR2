"""Copy selected real CouponCheck data into an ignored local workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inventory_couponcheck_real_data import (  # noqa: E402
    UPDATED_WORKBOOK_PATTERN,
    WORKBOOK_PATTERN,
    discover_day_dirs,
)

DEFAULT_OUTPUT_DIR = Path(".analysis_tmp/real_data")
DEFAULT_MANIFEST_NAME = "real_data_manifest.json"
DEFAULT_DAY_COUNT = 10


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-name", default=DEFAULT_MANIFEST_NAME)
    parser.add_argument("--days", help="Comma-separated YYYYMMDD list. Defaults to latest days.")
    parser.add_argument("--day-count", type=positive_int, default=DEFAULT_DAY_COUNT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-unsafe-output", action="store_true")
    return parser.parse_args(argv)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def prepare_real_data_workspace(
    *,
    source: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    manifest_name: str = DEFAULT_MANIFEST_NAME,
    days: list[str] | None = None,
    day_count: int = DEFAULT_DAY_COUNT,
    overwrite: bool = False,
    allow_unsafe_output: bool = False,
) -> dict[str, Any]:
    source = source.resolve()
    output_dir = output_dir.resolve()
    if not source.exists() or not source.is_dir():
        raise FileNotFoundError(f"source directory not found: {source}")
    validate_workspace_target(
        source=source,
        output_dir=output_dir,
        manifest_name=manifest_name,
        allow_unsafe_output=allow_unsafe_output,
    )
    selected_days = select_days(source, requested_days=days, day_count=day_count)
    if not selected_days:
        raise ValueError("no matching CouponCheck day folders found")

    manifest_path = output_dir / manifest_name
    if manifest_path.exists() and not overwrite:
        raise FileExistsError(f"manifest already exists: {manifest_path}")

    day_payloads = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for day, source_day_dir in selected_days:
        day_payloads.append(
            copy_day(
                source=source,
                day=day,
                source_day_dir=source_day_dir,
                output_dir=output_dir,
                overwrite=overwrite,
            )
        )

    manifest = {
        "status": "ready",
        "source": str(source),
        "output_dir": str(output_dir),
        "day_count": len(day_payloads),
        "days": day_payloads,
        "summary": {
            "png_count_total": sum(day["png_count"] for day in day_payloads),
            "copied_file_count": sum(day["copied_file_count"] for day in day_payloads),
        },
    }
    write_json_atomic(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def validate_workspace_target(
    *,
    source: Path,
    output_dir: Path,
    manifest_name: str,
    allow_unsafe_output: bool,
) -> None:
    validate_filename(manifest_name, ".json", "manifest_name")
    if output_dir == source or is_relative_to(output_dir, source):
        raise ValueError("output_dir must not be inside the source production folder")
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


def validate_filename(value: str, suffix: str, label: str) -> None:
    path = Path(value)
    if path.is_absolute() or path.name != value or path.parent != Path("."):
        raise ValueError(f"{label} must be a filename, not a path: {value}")
    if path.suffix.lower() != suffix:
        raise ValueError(f"{label} must end with {suffix}: {value}")


def select_days(
    source: Path,
    *,
    requested_days: list[str] | None,
    day_count: int,
) -> list[tuple[str, Path]]:
    discovered = discover_day_dirs(source)
    by_day = {day: path for day, path in discovered}
    if requested_days is None:
        return discovered[:day_count]
    missing = [day for day in requested_days if day not in by_day]
    if missing:
        raise ValueError("requested day folder not found: " + ", ".join(missing))
    return [(day, by_day[day]) for day in requested_days]


def copy_day(
    *,
    source: Path,
    day: str,
    source_day_dir: Path,
    output_dir: Path,
    overwrite: bool,
) -> dict[str, Any]:
    destination_day_dir = output_dir / day
    images_dir = destination_day_dir / "images"
    if destination_day_dir.exists() and not overwrite:
        raise FileExistsError(f"day workspace already exists: {destination_day_dir}")
    destination_day_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    workbook = source / WORKBOOK_PATTERN.format(day=day)
    updated_workbook = source / UPDATED_WORKBOOK_PATTERN.format(day=day)
    workbook_payload = copy_optional_file(workbook, destination_day_dir / workbook.name)
    updated_payload = copy_optional_file(
        updated_workbook,
        destination_day_dir / updated_workbook.name,
    )
    image_payloads = [
        copy_required_file(path, images_dir / path.name)
        for path in sorted(source_day_dir.glob("*.png"))
        if path.is_file()
    ]
    return {
        "day": day,
        "source_folder": str(source_day_dir),
        "workspace_folder": str(destination_day_dir),
        "workbook": workbook_payload,
        "updated_workbook": updated_payload,
        "png_count": len(image_payloads),
        "copied_file_count": int(workbook_payload["copied"])
        + int(updated_payload["copied"])
        + len(image_payloads),
        "images": image_payloads,
    }


def copy_optional_file(source: Path, destination: Path) -> dict[str, Any]:
    if not source.exists() or not source.is_file():
        return {"source": str(source), "destination": str(destination), "copied": False}
    return copy_required_file(source, destination)


def copy_required_file(source: Path, destination: Path) -> dict[str, Any]:
    source_hash = sha256_file(source)
    shutil.copy2(source, destination)
    destination_hash = sha256_file(destination)
    return {
        "source": str(source),
        "destination": str(destination),
        "copied": True,
        "size_bytes": source.stat().st_size,
        "source_sha256": source_hash,
        "copied_sha256": destination_hash,
        "hash_match": source_hash == destination_hash,
    }


def parse_days(value: str | None) -> list[str] | None:
    if value is None:
        return None
    days = [part.strip() for part in value.split(",") if part.strip()]
    invalid = [day for day in days if len(day) != 8 or not day.isdigit()]
    if invalid:
        raise ValueError("days must be comma-separated YYYYMMDD values")
    if not days:
        raise ValueError("days must include at least one YYYYMMDD value")
    return days


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = prepare_real_data_workspace(
            source=args.source,
            output_dir=args.output_dir,
            manifest_name=args.manifest_name,
            days=parse_days(args.days),
            day_count=args.day_count,
            overwrite=args.overwrite,
            allow_unsafe_output=args.allow_unsafe_output,
        )
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

