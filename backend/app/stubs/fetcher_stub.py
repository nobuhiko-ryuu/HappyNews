from app.ports.fetcher import ArticleFetcher, RawArticle
from datetime import datetime, timezone, timedelta


class StubArticleFetcher(ArticleFetcher):
    async def fetch(self, feed_url: str, source_id: str, source_name: str, limit: int = 50) -> list[RawArticle]:
        now = datetime.now(timezone.utc)
        return [
            RawArticle(
                url=f"https://example.com/article-{i}",
                title=f"Stub Article {i}: Something wonderful happened today",
                excerpt=f"This is a stub excerpt for article {i}. Something wonderful and positive happened that will make people smile and feel hopeful.",
                published_at=now - timedelta(hours=i),  # 各記事に異なる時刻
                source_id=source_id,
                source_name=source_name,
                thumbnail_url="https://via.placeholder.com/360x200",
                language_hint="en",
            )
            for i in range(limit)
        ]
