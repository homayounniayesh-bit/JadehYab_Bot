"""تشخیص و جداکردن تاریخ نوشتهشده کاربر از متن جستجو."""

from __future__ import annotations

import re

DATE_WORDS = (
    "امروز", "الان", "همین الان", "فعلا",
    "پسفردا", "پس فردا", "فردا", "روز بعد",
    "شنبه", "یکشنبه", "یک شنبه", "دوشنبه", "سهشنبه", "سه شنبه",
    "چهارشنبه", "چهار شنبه", "پنجشنبه", "پنج شنبه", "جمعه",
)

_DATE_PATTERN = re.compile(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}")
_DATE_SORTED = tuple(sorted(DATE_WORDS, key=len, reverse=True))


def looks_like_date(text: str) -> bool:
    value = (text or "").strip()
    return any(word in value for word in _DATE_SORTED) or bool(_DATE_PATTERN.search(value))


def split_date(text: str) -> tuple[str, str | None]:
    """تاریخ را از متن جدا میکند تا هم جستجو و هم پیشبینی درست شود."""
    value = (text or "").strip()
    found: str | None = None
    for word in _DATE_SORTED:
        if word in value:
            found = word
            value = value.replace(word, " ", 1)
            break
    if found is None:
        match = _DATE_PATTERN.search(value)
        if match:
            found = match.group(0)
            value = value[: match.start()] + " " + value[match.end() :]
    return re.sub(r"\s+", " ", value).strip(), found
