"""
Firestore コレクション設計（inputoutput_spec.md 準拠）

コレクション:
  sources/{source_id}
  configs/global
  runs/{run_id}
  candidates/{candidate_id}
  days/{day_key}
  articles/{article_id}
  users/{uid}
  users/{uid}/bookmarks/{article_id}
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Source:
    name: str
    type: str                    # rss | api | html
    feed_url: str
    homepage_url: str
    enabled: bool
    priority: int                # 1-100, 50が標準
    language_hint: str           # en | ja | unknown
    country_hint: str            # US | JP | unknown
    category_hint: str           # カテゴリセットから
    fetch_interval_minutes: int = 180
    consecutive_failures: int = 0
    quarantined: bool = False
    trust_score: int = 50
    notes: str = ""


@dataclass
class GlobalConfig:
    candidate_target_per_day: int = 200
    candidate_hard_limit_per_day: int = 500
    publish_count_per_day: int = 20
    fallback_max_days: int = 7
    per_category_max: dict = field(default_factory=lambda: {
        "science": 6, "health": 6, "environment": 6,
        "animals": 6, "community": 6, "technology": 5,
        "sports": 4, "culture": 4, "education": 5, "mixed": 8
    })
    ng_words: list[str] = field(default_factory=list)
    ng_source_ids: list[str] = field(default_factory=list)
    ng_categories: list[str] = field(default_factory=list)
    summary_rule: dict = field(default_factory=lambda: {
        "lines": 3,
        "chars_per_line_min": 25,
        "chars_per_line_max": 40,
        "banned_phrases": ["衝撃", "炎上", "閲覧注意"]
    })
    notification_time_granularity: str = "hour"


@dataclass
class Article:
    id: str
    source_name: str
    source_url: str
    original_url: str
    title: str
    summary_3lines: str
    thumbnail_url: Optional[str]
    published_at: str            # ISO8601
    collected_at: str            # ISO8601
    tags: list[str]
    category: str
    happy_score: float
    language: str
    day_key: str                 # YYYY-MM-DD


@dataclass
class Day:
    day_key: str
    article_ids: list[str]
    published_at: str            # ISO8601
    stats: dict
