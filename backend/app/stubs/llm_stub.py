from app.ports.llm import ArticleClassifier, ArticleSummarizer, ClassifyResult, SummaryResult

CATEGORIES = ["science", "health", "environment", "animals", "education",
              "community", "technology", "sports", "culture", "mixed"]

class StubArticleClassifier(ArticleClassifier):
    def __init__(self):
        self._counter = 0

    async def classify(self, title: str, excerpt: str, language: str) -> ClassifyResult:
        # カテゴリを分散させてカテゴリ上限テストが機能するようにする
        cat = CATEGORIES[self._counter % len(CATEGORIES)]
        self._counter += 1
        return ClassifyResult(
            happy_score=0.80 + (self._counter % 10) * 0.01,
            category=cat,
            tags=["前向き", "進歩", cat],
            is_ng=False,
        )

class StubArticleSummarizer(ArticleSummarizer):
    async def summarize(self, title: str, excerpt: str, language: str) -> SummaryResult:
        return SummaryResult(
            title_ja=f"{title[:25]}",
            summary_3lines="世界で素晴らしいことが起きました。\n多くの人が恩恵を受けています。\n今後もこの流れが続く見込みです。",
        )
