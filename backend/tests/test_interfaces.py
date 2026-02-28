"""
TEST-001~003: 外部インタフェースとStubのテスト（外部依存ゼロ）
"""
import os
os.environ["EXTERNAL_MODE"] = "stub"

import pytest
from app.ports.fetcher import RawArticle
from app.ports.llm import ClassifyResult, SummaryResult
from app.ports.notifier import NotificationPayload
from app.container import get_fetcher, get_classifier, get_summarizer, get_notifier


@pytest.mark.asyncio
async def test_stub_fetcher_returns_raw_articles():
    fetcher = get_fetcher()
    articles = await fetcher.fetch("https://example.com/feed", "test-source", "Test Source", limit=10)
    assert len(articles) == 10
    assert all(isinstance(a, RawArticle) for a in articles)
    assert all(a.url.startswith("https://") for a in articles)
    assert all(len(a.excerpt) > 0 for a in articles)


@pytest.mark.asyncio
async def test_stub_fetcher_respects_limit():
    fetcher = get_fetcher()
    articles = await fetcher.fetch("https://example.com/feed", "test-source", "Test Source", limit=5)
    assert len(articles) == 5


@pytest.mark.asyncio
async def test_stub_classifier_returns_valid_result():
    classifier = get_classifier()
    result = await classifier.classify(
        title="Scientists discover new treatment for rare disease",
        excerpt="Researchers have found a breakthrough treatment...",
        language="en"
    )
    assert isinstance(result, ClassifyResult)
    assert 0.0 <= result.happy_score <= 1.0
    assert result.category in [
        "science", "health", "environment", "animals", "education",
        "community", "technology", "sports", "culture", "mixed"
    ]
    assert isinstance(result.tags, list)
    assert isinstance(result.is_ng, bool)


@pytest.mark.asyncio
async def test_stub_summarizer_returns_3_lines():
    summarizer = get_summarizer()
    result = await summarizer.summarize(
        title="Good news for the environment",
        excerpt="Forests are recovering faster than expected...",
        language="en"
    )
    assert isinstance(result, SummaryResult)
    assert len(result.title_ja) > 0
    lines = result.summary_3lines.split("\n")
    assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}: {result.summary_3lines!r}"
    assert all(len(line) > 0 for line in lines)


@pytest.mark.asyncio
async def test_stub_notifier_returns_success_counts():
    notifier = get_notifier()
    tokens = ["token1", "token2", "token3"]
    payload = NotificationPayload(title="今日のハッピーニュース", body="世界の良い出来事を20本まとめました", day_key="2026-03-01")
    result = await notifier.send_multicast(tokens, payload)
    assert result["success"] == 3
    assert result["failure"] == 0


def test_container_returns_stub_by_default():
    """EXTERNAL_MODE=stub のとき、全コンテナがStubを返す"""
    fetcher = get_fetcher()
    classifier = get_classifier()
    summarizer = get_summarizer()
    notifier = get_notifier()
    assert "Stub" in type(fetcher).__name__
    assert "Stub" in type(classifier).__name__
    assert "Stub" in type(summarizer).__name__
    assert "Stub" in type(notifier).__name__
