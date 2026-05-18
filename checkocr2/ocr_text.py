"""OCR text normalization helpers."""

from __future__ import annotations

import re
from datetime import datetime

from .ocr_runtime_options import DEFAULT_RATE_DECIMAL_PLACES, normalize_rate_decimal_places

DATE_FULLMATCH_RE = re.compile(r"\d{4}/\d{2}/\d{2}")
RATE_FULLMATCH_RE = re.compile(r"\d+\.\d+")
DATE_FIND_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})\D*(\d{1,2})\D*(\d{1,2})(?!\d)")
NON_DIGIT_RE = re.compile(r"[^\d]")
NON_DIGIT_DOT_RE = re.compile(r"[^\d.]")
RATE_DIGIT_DOT_MATCH_RE = re.compile(r"\d+\.\d+")
RATE_DIGIT_DOT_END_MATCH_RE = re.compile(r"\d+\.")
RATE_DIGIT_MATCH_RE = re.compile(r"\d+")

# str.maketrans is significantly faster than chaining multiple .replace() calls
RATE_TRANSLATION = str.maketrans({
    "%": "",
    " ": "",
    ",": ".",
    "쨌": ".",
    "·": ".",
    "ㆍ": "."
})


def is_valid_date_format(value: str) -> bool:
    if not DATE_FULLMATCH_RE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y/%m/%d")
    except ValueError:
        return False
    return True


def is_valid_rate_format(value: str) -> bool:
    return bool(RATE_FULLMATCH_RE.fullmatch(value))


def clean_date_text(text: str) -> str:
    for match in DATE_FIND_RE.finditer(text):
        year, month, day = match.groups()
        candidate = f"{year}/{month.zfill(2)}/{day.zfill(2)}"
        if is_valid_date_format(candidate):
            return candidate

    cleaned = NON_DIGIT_RE.sub("", text)
    for start in range(0, max(0, len(cleaned) - 7)):
        chunk = cleaned[start : start + 8]
        if len(chunk) < 8:
            continue
        if not chunk.startswith(("19", "20")):
            continue
        candidate = f"{chunk[:4]}/{chunk[4:6]}/{chunk[6:]}"
        if is_valid_date_format(candidate):
            return candidate
    if len(cleaned) == 8:
        return f"{cleaned[:4]}/{cleaned[4:6]}/{cleaned[6:]}"
    if len(cleaned) == 6:
        year_prefix = "20" if int(cleaned[:2]) < 70 else "19"
        return f"{year_prefix}{cleaned[:2]}/{cleaned[2:4]}/{cleaned[4:]}"
    if len(cleaned) == 7 and cleaned.startswith("202") and int(cleaned[4]) <= 1:
        month_part = cleaned[4]
        day_part = cleaned[5:]
        if len(day_part) == 1:
            day_part = "0" + day_part
        if len(day_part) == 2 and int(day_part) > 31 and len(cleaned) == 7:
            return f"{cleaned[:4]}/{cleaned[4:6]}/{cleaned[6].zfill(2)}"
        return f"{cleaned[:4]}/{month_part.zfill(2)}/{day_part.zfill(2)}"
    return text


def clean_rate_text(text: str, precision: int = DEFAULT_RATE_DECIMAL_PLACES) -> str:
    precision = normalize_rate_decimal_places(precision)
    # Using str.translate with maketrans gives ~3x speedup vs chaining 6 replace() calls
    cleaned = text.translate(RATE_TRANSLATION)
    # Using pre-compiled regex avoids recompiling the pattern on every function call
    cleaned = NON_DIGIT_DOT_RE.sub("", cleaned)

    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = parts[0] + "." + "".join(parts[1:])

    if RATE_DIGIT_DOT_MATCH_RE.fullmatch(cleaned):
        try:
            return f"{float(cleaned):.{precision}f}"
        except ValueError:
            return cleaned
    if RATE_DIGIT_DOT_END_MATCH_RE.fullmatch(cleaned):
        try:
            return f"{float(cleaned[:-1]):.{precision}f}"
        except ValueError:
            return cleaned[:-1]
    if RATE_DIGIT_MATCH_RE.fullmatch(cleaned):
        if len(cleaned) == 1:
            return f"{cleaned}.{('0' * precision)}"
        if len(cleaned) <= 6:
            # CouponCheck rates in this repo stay below 10, so digit-only OCR output
            # is usually a missing decimal point rather than a missing leading digit.
            candidate = f"{cleaned[0]}.{cleaned[1:]}"
            try:
                return f"{float(candidate):.{precision}f}"
            except ValueError:
                return candidate
    return cleaned
