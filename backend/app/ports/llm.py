from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ClassifyResult:
    happy_score: float    # 0.0〜1.0
    category: str         # science/health/environment/animals/education/community/technology/sports/culture/mixed
    tags: list[str]
    is_ng: bool
    reason: Optional[str] = None

@dataclass
class SummaryResult:
    title_ja: str         # 整形後タイトル
    summary_3lines: str   # 日本語3行要約（\n区切り）

class ArticleClassifier(ABC):
    @abstractmethod
    async def classify(self, title: str, excerpt: str, language: str) -> ClassifyResult:
        """happy_score / category / tags / is_ng を付与する"""
        ...

class ArticleSummarizer(ABC):
    @abstractmethod
    async def summarize(self, title: str, excerpt: str, language: str) -> SummaryResult:
        """日本語3行要約を生成する"""
        ...
