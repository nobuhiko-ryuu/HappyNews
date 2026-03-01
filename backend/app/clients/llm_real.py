"""Real LLM clients using OpenAI gpt-4o-mini"""
from __future__ import annotations
import json
import logging
import os

from app.ports.llm import ArticleClassifier, ArticleSummarizer, ClassifyResult, SummaryResult

logger = logging.getLogger("happynews.clients.llm_real")

_CLASSIFY_SYSTEM = (
    "You are a news classifier. Given a news article title and excerpt, "
    "respond with valid JSON only.\n"
    'Respond with: {"happy_score": <float 0.0-1.0>, '
    '"category": <science|health|environment|animals|education|community|technology|sports|culture|mixed>, '
    '"tags": [<up to 5 strings>], '
    '"is_ng": <true if violent/political/disaster/crime>, '
    '"reason": <short reason string>}'
)

_SUMMARIZE_SYSTEM = (
    "You are a Japanese news summarizer. Summarize the article in Japanese in exactly 3 lines "
    "(separated by \\n). Also provide a Japanese title. Respond with valid JSON only.\n"
    'Respond with: {"title_ja": "<Japanese title>", "summary_3lines": "<line1>\\n<line2>\\n<line3>"}'
)


def _get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=api_key)


class RealArticleClassifier(ArticleClassifier):
    async def classify(self, title: str, excerpt: str, language: str) -> ClassifyResult:
        client = _get_client()
        user_msg = f"Title: {title}\nExcerpt: {excerpt[:300]}\nLanguage: {language}"
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
        )
        data = json.loads(response.choices[0].message.content)
        return ClassifyResult(
            happy_score=float(data.get("happy_score", 0.0)),
            category=data.get("category", "mixed"),
            tags=data.get("tags", []),
            is_ng=bool(data.get("is_ng", False)),
            reason=data.get("reason"),
        )


class RealArticleSummarizer(ArticleSummarizer):
    async def summarize(self, title: str, excerpt: str, language: str) -> SummaryResult:
        client = _get_client()
        user_msg = f"Title: {title}\nExcerpt: {excerpt[:500]}\nLanguage: {language}"
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SUMMARIZE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
        data = json.loads(response.choices[0].message.content)
        return SummaryResult(
            title_ja=data.get("title_ja", title),
            summary_3lines=data.get("summary_3lines", ""),
        )
