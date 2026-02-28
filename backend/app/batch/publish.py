"""BE-041: Publish - days/articles を原子的に確定保存"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from app.db.firestore_client import get_db

logger = logging.getLogger("happynews.batch.publish")


async def publish_articles(
    day_key: str,
    articles: list[dict],
    dry_run: bool = False,
) -> list[str]:
    """
    articles を Firestore に保存し、days/{day_key} を確定。
    失敗時は days/{day_key} を壊さない（既存データを温存）。
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would publish {len(articles)} articles for {day_key}")
        return [f"dry-{i}" for i in range(len(articles))]

    db = get_db()
    article_ids = []
    now = datetime.now(timezone.utc).isoformat()

    # 既存の days/{day_key} を確認（冪等性）
    existing_day = await db.collection("days").document(day_key).get()
    if existing_day.exists:
        logger.warning(f"days/{day_key} already exists, overwriting")

    # 1. articles を保存（個別失敗してもスキップ）
    batch = db.batch()
    for i, article in enumerate(articles):
        article_id = str(uuid.uuid4())
        article_ids.append(article_id)
        ref = db.collection("articles").document(article_id)
        batch.set(ref, {
            "title": article.get("title", ""),
            "summary_3lines": article.get("summary_3lines", ""),
            "source_name": article.get("source_name", ""),
            "source_url": "",
            "original_url": article.get("original_url", ""),
            "thumbnail_url": None,  # MVP: 外部直リンクは将来対応
            "published_at": article.get("published_at") or now,
            "collected_at": article.get("collected_at", now),
            "tags": article.get("llm_tags", []),
            "category": article.get("llm_category", "mixed"),
            "happy_score": article.get("llm_happy_score", 0.0),
            "language": article.get("lang", "en"),
            "day_key": day_key,
        })
        if (i + 1) % 499 == 0:
            await batch.commit()
            batch = db.batch()
    await batch.commit()

    # 2. days/{day_key} を確定
    await db.collection("days").document(day_key).set({
        "day_key": day_key,
        "article_ids": article_ids,
        "published_at": now,
        "stats": {"count": len(article_ids)},
    })

    logger.info(f"Published {len(article_ids)} articles for {day_key}")
    return article_ids
