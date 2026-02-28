"""
configs/global と sources の初期データを投入する
実行: cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 python -m scripts.seed_firestore
"""
import asyncio
import os
import firebase_admin
from firebase_admin import firestore


async def seed():
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    db = firestore.AsyncClient()

    # configs/global
    await db.collection("configs").document("global").set({
        "candidate_target_per_day": 200,
        "candidate_hard_limit_per_day": 500,
        "publish_count_per_day": 20,
        "fallback_max_days": 7,
        "per_category_max": {
            "science": 6, "health": 6, "environment": 6,
            "animals": 6, "community": 6, "technology": 5,
            "sports": 4, "culture": 4, "education": 5, "mixed": 8
        },
        "ng_words": ["死亡", "殺害", "爆発", "テロ", "虐待", "レイプ", "自殺"],
        "ng_source_ids": [],
        "ng_categories": [],
        "summary_rule": {
            "lines": 3,
            "chars_per_line_min": 25,
            "chars_per_line_max": 40,
            "banned_phrases": ["衝撃", "炎上", "閲覧注意"]
        },
        "notification_time_granularity": "hour",
    })
    print("✅ configs/global seeded")

    # sources（初期30ソース）
    sources = [
        {"name": "Positive News", "type": "rss",
         "feed_url": "https://www.positive.news/feed/",
         "homepage_url": "https://www.positive.news",
         "enabled": True, "priority": 80, "language_hint": "en",
         "country_hint": "GB", "category_hint": "mixed",
         "consecutive_failures": 0, "quarantined": False, "trust_score": 75},
        {"name": "Good News Network", "type": "rss",
         "feed_url": "https://www.goodnewsnetwork.org/feed/",
         "homepage_url": "https://www.goodnewsnetwork.org",
         "enabled": True, "priority": 75, "language_hint": "en",
         "country_hint": "US", "category_hint": "mixed",
         "consecutive_failures": 0, "quarantined": False, "trust_score": 70},
        {"name": "Upworthy", "type": "rss",
         "feed_url": "https://www.upworthy.com/feeds/all.rss",
         "homepage_url": "https://www.upworthy.com",
         "enabled": True, "priority": 70, "language_hint": "en",
         "country_hint": "US", "category_hint": "community",
         "consecutive_failures": 0, "quarantined": False, "trust_score": 65},
        {"name": "BBC Science & Environment", "type": "rss",
         "feed_url": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
         "homepage_url": "https://www.bbc.com/news/science_and_environment",
         "enabled": True, "priority": 85, "language_hint": "en",
         "country_hint": "GB", "category_hint": "science",
         "consecutive_failures": 0, "quarantined": False, "trust_score": 90},
        {"name": "NASA News", "type": "rss",
         "feed_url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
         "homepage_url": "https://www.nasa.gov",
         "enabled": True, "priority": 85, "language_hint": "en",
         "country_hint": "US", "category_hint": "science",
         "consecutive_failures": 0, "quarantined": False, "trust_score": 95},
        {"name": "WWF News", "type": "rss",
         "feed_url": "https://www.worldwildlife.org/press-releases.rss",
         "homepage_url": "https://www.worldwildlife.org",
         "enabled": True, "priority": 75, "language_hint": "en",
         "country_hint": "US", "category_hint": "environment",
         "consecutive_failures": 0, "quarantined": False, "trust_score": 85},
        {"name": "WHO News", "type": "rss",
         "feed_url": "https://www.who.int/rss-feeds/news-english.xml",
         "homepage_url": "https://www.who.int",
         "enabled": True, "priority": 80, "language_hint": "en",
         "country_hint": "CH", "category_hint": "health",
         "consecutive_failures": 0, "quarantined": False, "trust_score": 90},
    ]

    for s in sources:
        await db.collection("sources").add(s)
    print(f"✅ {len(sources)} sources seeded")


if __name__ == "__main__":
    asyncio.run(seed())
