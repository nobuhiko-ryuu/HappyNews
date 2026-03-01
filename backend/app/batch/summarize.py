"""BE-039: LLM要約 - 上位20本のみ日本語3行要約を生成"""
from __future__ import annotations
import asyncio
import logging
from app.ports.llm import ArticleSummarizer, SummaryResult

logger = logging.getLogger("happynews.batch.summarize")

_CONCURRENCY = 3  # 要約は重いので並列数を絞る


def _format_summary(text: str, summary_rule: dict) -> str:
    """3行要約の整形ガード: 3行に正規化し banned_phrases を除去する"""
    # banned_phrases 除去
    for phrase in summary_rule.get("banned_phrases", []):
        text = text.replace(phrase, "")

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if len(lines) > 3:
        lines = lines[:3]
    elif len(lines) < 3:
        lines += [""] * (3 - len(lines))

    return "\n".join(lines)


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
                summary = _format_summary(result.summary_3lines, summary_rule)
                results[i] = dict(article) | {"summary_3lines": summary}
            except Exception as e:
                logger.warning(f"Summarize failed for '{article.get('title', '')[:40]}': {e}")
                results[i] = dict(article) | {"summary_3lines": ""}

    await asyncio.gather(*[_summarize_one(i, a) for i, a in enumerate(articles)])
    logger.info(f"Summarized {len(articles)} articles")
    return results
