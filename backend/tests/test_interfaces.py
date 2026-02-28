"""
TEST-001~003: 外部インタフェースとStubのテスト（外部依存ゼロ）
"""
import pytest
from app.ports.fetcher import RawArticle
from app.ports.llm import ClassifyResult, SummaryResult
from app.ports.notifier import NotificationPayload
from app.stubs.fetcher_stub import StubArticleFetcher
from app.stubs.llm_stub import StubArticleClassifier, StubArticleSummarizer
from app.stubs.notifier_stub import StubPushNotifier


@pytest.fixture(autouse=True)
def force_stub_mode(monkeypatch):
    """全テストで EXTERNAL_MODE=stub を強制"""
    monkeypatch.setenv("EXTERNAL_MODE", "stub")


def test_container_returns_stub_by_default(monkeypatch):
    """EXTERNAL_MODE=stub のとき、全コンテナがStubを返す"""
    monkeypatch.setenv("EXTERNAL_MODE", "stub")
    from app.container import get_fetcher, get_classifier, get_summarizer, get_notifier
    assert isinstance(get_fetcher(), StubArticleFetcher)
    assert isinstance(get_classifier(), StubArticleClassifier)
    assert isinstance(get_summarizer(), StubArticleSummarizer)
    assert isinstance(get_notifier(), StubPushNotifier)


@pytest.mark.asyncio
async def test_stub_fetcher_returns_raw_articles():
    fetcher = StubArticleFetcher()
    articles = await fetcher.fetch("https://example.com/feed", "test-source", "Test Source", limit=10)
    assert len(articles) == 10
    assert all(isinstance(a, RawArticle) for a in articles)
    assert all(a.url.startswith("https://") for a in articles)
    assert all(len(a.excerpt) > 0 for a in articles)


@pytest.mark.asyncio
async def test_stub_fetcher_respects_limit():
    fetcher = StubArticleFetcher()
    articles = await fetcher.fetch("https://example.com/feed", "test-source", "Test Source", limit=5)
    assert len(articles) == 5


@pytest.mark.asyncio
async def test_stub_fetcher_returns_different_published_at():
    """各記事が異なる published_at を持つことを確認（ソートテスト対応）"""
    fetcher = StubArticleFetcher()
    articles = await fetcher.fetch("https://example.com/feed", "test-source", "Test Source", limit=5)
    timestamps = [a.published_at for a in articles]
    assert len(set(timestamps)) == 5, "各記事は異なる published_at を持つべき"


@pytest.mark.asyncio
async def test_stub_classifier_returns_valid_result():
    classifier = StubArticleClassifier()
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
async def test_stub_classifier_cycles_through_categories():
    """複数呼び出しでカテゴリが分散することを確認"""
    classifier = StubArticleClassifier()
    categories = set()
    for i in range(10):
        result = await classifier.classify(f"Title {i}", f"Excerpt {i}", "en")
        categories.add(result.category)
    assert len(categories) > 1, "カテゴリが分散すること"


@pytest.mark.asyncio
async def test_stub_summarizer_returns_3_lines():
    summarizer = StubArticleSummarizer()
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
    notifier = StubPushNotifier()
    tokens = ["token1", "token2", "token3"]
    payload = NotificationPayload(title="今日のハッピーニュース", body="世界の良い出来事を20本まとめました", day_key="2026-03-01")
    result = await notifier.send_multicast(tokens, payload)
    assert result["success"] == 3
    assert result["failure"] == 0
