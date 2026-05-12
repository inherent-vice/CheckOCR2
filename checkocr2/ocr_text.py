"""OCR text normalization helpers."""

from __future__ import annotations

import re
from datetime import datetime


def is_valid_date_format(value: str) -> bool:
    if not re.fullmatch(r"\d{4}/\d{2}/\d{2}", value):
        return False
    try:
        datetime.strptime(value, "%Y/%m/%d")
    except ValueError:
        return False
    return True


def is_valid_rate_format(value: str) -> bool:
    return bool(re.fullmatch(r"\d+\.\d+", value))


def clean_date_text(text: str) -> str:
    cleaned = re.sub(r"[^\d]", "", text)
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


def clean_rate_text(text: str) -> str:
    cleaned = (
        text.replace("%", "")
        .replace(" ", "")
        .replace(",", ".")
        .replace("·", ".")
        .replace("쨌", ".")
    )
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = parts[0] + "." + "".join(parts[1:])

    if re.fullmatch(r"\d+\.\d+", cleaned):
        try:
            return f"{float(cleaned):.3f}"
        except ValueError:
            return cleaned
    if re.fullmatch(r"\d+", cleaned) and 2 <= len(cleaned) <= 5:
        if len(cleaned) == 2:
            return f"{cleaned[0]}.{cleaned[1]}00"
        if len(cleaned) == 3:
            return f"{cleaned[0]}.{cleaned[1:]}0" if cleaned[1:] != "00" else f"{cleaned[0]}.000"
        if len(cleaned) == 4:
            return f"{cleaned[0]}.{cleaned[1:]}"
        if len(cleaned) == 5:
            return f"{cleaned[:2]}.{cleaned[2:]}"
    return cleaned
