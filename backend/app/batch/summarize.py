"""BE-039: LLM要約 - 上位20本のみ日本語3行要約を生成"""
from __future__ import annotations
import asyncio
import logging
from app.ports.llm import ArticleSummarizer, SummaryResult

logger = logging.getLogger("happynews.batch.summarize")

_CONCURRENCY = 3  # 要約は重いので並列数を絞る


async def summarize_articles(
    articles: list[dict],
    summarizer: ArticleSummarizer,
    summary_rule: dict | None = None,
) -> list[dict]:
    """
    選出された記事に日本語3行要約を付与。
    summary_rule: lines/chars_per_line_max/banned_phrases 等
    """
    summary_rule = summary_rule or {}
    sem = asyncio.Semaphore(_CONCURRENCY)
    results = list(articles)

    async def _summarize_one(i: int, article: dict) -> None:
        async with sem:
            try:
                result: SummaryResult = await summarizer.summarize(
                    title=article.get("title", ""),
                    excerpt=article.get("excerpt", ""),
                    language=article.get("lang", "en"),
                )
                results[i] = dict(article) | {"summary_3lines": result.summary_3lines}
            except Exception as e:
                logger.warning(f"Summarize failed for '{article.get('title', '')[:40]}': {e}")
                results[i] = dict(article) | {"summary_3lines": ""}

    await asyncio.gather(*[_summarize_one(i, a) for i, a in enumerate(articles)])
    logger.info(f"Summarized {len(articles)} articles")
    return results
