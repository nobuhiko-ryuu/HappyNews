"""Real ArticleFetcher using feedparser"""
from __future__ import annotations
import asyncio
import calendar
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

import feedparser

from app.ports.fetcher import ArticleFetcher, RawArticle

logger = logging.getLogger("happynews.clients.fetcher_real")
_executor = ThreadPoolExecutor(max_workers=4)


def _parse_feed(url: str) -> feedparser.FeedParserDict:
    return feedparser.parse(url)


def _extract_thumbnail(entry) -> Optional[str]:
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            if media.get("url") and media.get("medium") in ("image", None):
                return media["url"]
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("href") or enc.get("url")
    return None


def _published_at(entry) -> Optional[datetime]:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            ts = calendar.timegm(entry.published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass
    return None


def _excerpt(entry) -> str:
    text = ""
    if hasattr(entry, "content") and entry.content:
        text = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        text = entry.summary or ""
    text = re.sub(r"<[^>]+>", " ", text)
    return text[:500].strip()


class RealArticleFetcher(ArticleFetcher):
    async def fetch(
        self,
        feed_url: str,
        source_id: str,
        source_name: str,
        limit: int = 50,
    ) -> list[RawArticle]:
        loop = asyncio.get_event_loop()
        try:
            feed = await loop.run_in_executor(_executor, _parse_feed, feed_url)
        except Exception as e:
            logger.error(f"Failed to parse feed {feed_url}: {e}")
            return []

        articles = []
        for entry in feed.entries[:limit]:
            url = entry.get("link") or entry.get("id") or ""
            if not url:
                continue
            articles.append(
                RawArticle(
                    url=url,
                    title=entry.get("title", ""),
                    excerpt=_excerpt(entry),
                    published_at=_published_at(entry),
                    source_id=source_id,
                    source_name=source_name,
                    thumbnail_url=_extract_thumbnail(entry),
                    language_hint="unknown",
                )
            )
        return articles
