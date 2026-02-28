from app.ports.fetcher import ArticleFetcher, RawArticle
from datetime import datetime, timezone

STUB_ARTICLES = [
    RawArticle(
        url=f"https://example.com/article-{i}",
        title=f"Stub Article {i}: Something wonderful happened today",
        excerpt=f"This is a stub excerpt for article {i}. Something wonderful and positive happened that will make people smile.",
        published_at=datetime.now(timezone.utc),
        source_id="stub-source",
        source_name="Stub Good News",
        thumbnail_url="https://via.placeholder.com/360x200",
        language_hint="en",
    )
    for i in range(1, 51)
]

class StubArticleFetcher(ArticleFetcher):
    async def fetch(self, feed_url: str, source_id: str, source_name: str, limit: int = 50) -> list[RawArticle]:
        return STUB_ARTICLES[:limit]
