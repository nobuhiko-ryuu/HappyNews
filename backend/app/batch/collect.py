"""BE-033: Collect - RSS/APIソースから候補記事を収集する"""
from __future__ import annotations
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from app.ports.fetcher import ArticleFetcher, RawArticle
from app.db.firestore_client import get_db

logger = logging.getLogger("happynews.batch.collect")


async def collect_candidates(
    fetcher: ArticleFetcher,
    day_key: str,
    target: int = 200,
    hard_limit: int = 500,
    dry_run: bool = False,
) -> list[dict]:
    """
    sources コレクションの enabled=true を priority 降順で巡回し候補を収集する。
    target に達したら収集終了。hard_limit を超えたら打ち切り。
    """
    db = get_db()
    # sources を priority 降順で取得
    sources_query = db.collection("sources").where("enabled", "==", True).order_by("priority", direction="DESCENDING")
    sources = [doc.to_dict() | {"_id": doc.id} async for doc in sources_query.stream()]

    collected: list[dict] = []
    seen_urls: set[str] = set()

    for source in sources:
        if len(collected) >= hard_limit:
            logger.warning(f"Hard limit {hard_limit} reached, stopping collection")
            break
        if len(collected) >= target:
            logger.info(f"Target {target} reached after {len(sources)} sources")
            break

        try:
            remaining = min(target - len(collected), hard_limit - len(collected))
            articles: list[RawArticle] = await fetcher.fetch(
                source["feed_url"],
                source_id=source["_id"],
                source_name=source.get("name", ""),
                limit=min(remaining, 50),
            )
        except Exception as e:
            logger.warning(f"Failed to fetch {source.get('name')}: {e}")
            continue

        for article in articles:
            url = _normalize_url(article.url)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            doc_id = _candidate_doc_id(url, source["_id"])
            now_utc = datetime.now(timezone.utc)
            candidate = {
                "_candidate_id": doc_id,
                "day_key": day_key,
                "source_id": source["_id"],
                "source_name": source.get("name", ""),
                "source_url": source.get("homepage_url", ""),
                "original_url": url,
                "title": article.title,
                "excerpt": article.excerpt[:500] if article.excerpt else "",
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "collected_at": now_utc.isoformat(),
                "ttl_delete_at": (now_utc + timedelta(days=7)).isoformat(),
                "thumbnail_url": article.thumbnail_url,
                "lang": source.get("language_hint", "en"),
                "rule_filtered": False,
                "rule_filter_reasons": [],
                "llm_happy_score": 0.0,
                "llm_category": "",
                "llm_tags": [],
                "llm_is_ng": False,
            }
            collected.append(candidate)

    logger.info(f"Collected {len(collected)} candidates from {len(sources)} sources")

    if not dry_run:
        # Firestore に保存（バッチ書き込み・冪等）
        batch = db.batch()
        for i, c in enumerate(collected):
            doc_id = c["_candidate_id"]
            ref = db.collection("candidates").document(doc_id)
            # _candidate_id はメモリ上の参照用、Firestore フィールドには含めない
            batch.set(ref, {k: v for k, v in c.items() if k != "_candidate_id"})
            if (i + 1) % 499 == 0:  # Firestore バッチ上限
                await batch.commit()
                batch = db.batch()
        await batch.commit()

    return collected


def _candidate_doc_id(url: str, source_id: str) -> str:
    """URL + source_id から決定論的な Firestore doc ID を生成（冪等収集）"""
    key = f"{url}|{source_id}"
    return hashlib.md5(key.encode()).hexdigest()


def _normalize_url(url: str) -> str:
    """URLの正規化（クエリパラメータのトラッキング系を除去）"""
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
    try:
        parsed = urlparse(url)
        # utm_* などトラッキング系パラメータを除去
        params = {k: v for k, v in parse_qs(parsed.query).items()
                  if not k.startswith("utm_")}
        normalized = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
        return normalized.rstrip("/")
    except Exception:
        return url
