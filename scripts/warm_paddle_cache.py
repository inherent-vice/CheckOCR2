"""Warm PaddleOCR model cache before the first operator run."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from checkocr2.startup_trace import paddle_model_cache_state  # noqa: E402

DEFAULT_MODELS = ("korean_PP-OCRv5_mobile_rec",)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args(argv)


def language_for_model(model_name: str) -> list[str]:
    return ["ko", "en"] if model_name.startswith("korean_") else ["en"]


def warm_paddle_cache(
    model_names: list[str],
    *,
    cache_dir: Path | None = None,
    dry_run: bool = False,
    reader_factory: Any = None,
) -> dict[str, Any]:
    old_cache_dir = os.environ.get("PADDLE_PDX_CACHE_HOME")
    if cache_dir is not None:
        os.environ["PADDLE_PDX_CACHE_HOME"] = str(cache_dir)

    try:
        before = paddle_model_cache_state(model_names)
        warmed: list[dict[str, Any]] = []

        if not dry_run:
            if reader_factory is None:
                from checkocr2.ocr_paddle_engine import create_paddle_text_recognition_reader

                reader_factory = create_paddle_text_recognition_reader
            old_model = os.environ.get("CHECKOCR2_PADDLE_REC_MODEL")
            try:
                for model_name in model_names:
                    os.environ["CHECKOCR2_PADDLE_REC_MODEL"] = model_name
                    reader = reader_factory(language_for_model(model_name), gpu=False)
                    close = getattr(getattr(reader, "reader", reader), "close", None)
                    if callable(close):
                        close()
                    warmed.append({"model": model_name, "status": "ok"})
            finally:
                if old_model is None:
                    os.environ.pop("CHECKOCR2_PADDLE_REC_MODEL", None)
                else:
                    os.environ["CHECKOCR2_PADDLE_REC_MODEL"] = old_model

        after = paddle_model_cache_state(model_names)
        success = dry_run or len(warmed) == len(model_names)
        return {
            "status": "ok" if success else "error",
            "dry_run": dry_run,
            "cache_before": before,
            "cache_after": after,
            "warmed": warmed,
        }
    finally:
        if old_cache_dir is None:
            os.environ.pop("PADDLE_PDX_CACHE_HOME", None)
        else:
            os.environ["PADDLE_PDX_CACHE_HOME"] = old_cache_dir


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = warm_paddle_cache(
        list(args.models),
        cache_dir=args.cache_dir,
        dry_run=args.dry_run,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
