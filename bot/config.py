from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    token: str = os.getenv("BOT_TOKEN", "").strip()
    search_timeout: float = _get_float("SEARCH_TIMEOUT", 12.0)
    max_results: int = _get_int("MAX_RESULTS", 8)
    recent_days: int = _get_int("RECENT_DAYS", 14)
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()


settings = Settings()
