from __future__ import annotations
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def today_jst() -> str:
    """JST基準の今日の day_key（YYYY-MM-DD）を返す"""
    return datetime.now(JST).strftime("%Y-%m-%d")


def is_valid_day_key(day_key: str) -> bool:
    try:
        datetime.strptime(day_key, "%Y-%m-%d")
        return True
    except ValueError:
        return False
