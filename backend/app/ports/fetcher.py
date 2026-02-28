from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class RawArticle:
    url: str
    title: str
    excerpt: str          # 数百文字まで（全文保存しない）
    published_at: Optional[datetime]
    source_id: str
    source_name: str
    thumbnail_url: Optional[str]
    language_hint: str = "unknown"

class ArticleFetcher(ABC):
    @abstractmethod
    async def fetch(self, feed_url: str, source_id: str, source_name: str, limit: int = 50) -> list[RawArticle]:
        """RSS/APIからRawArticleリストを取得する"""
        ...
