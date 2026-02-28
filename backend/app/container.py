import os
from app.ports.fetcher import ArticleFetcher
from app.ports.llm import ArticleClassifier, ArticleSummarizer
from app.ports.notifier import PushNotifier

EXTERNAL_MODE = os.getenv("EXTERNAL_MODE", "stub")  # stub | real

def get_fetcher() -> ArticleFetcher:
    if EXTERNAL_MODE == "real":
        from app.clients.fetcher_real import RealArticleFetcher
        return RealArticleFetcher()
    from app.stubs.fetcher_stub import StubArticleFetcher
    return StubArticleFetcher()

def get_classifier() -> ArticleClassifier:
    if EXTERNAL_MODE == "real":
        from app.clients.llm_real import RealArticleClassifier
        return RealArticleClassifier()
    from app.stubs.llm_stub import StubArticleClassifier
    return StubArticleClassifier()

def get_summarizer() -> ArticleSummarizer:
    if EXTERNAL_MODE == "real":
        from app.clients.llm_real import RealArticleSummarizer
        return RealArticleSummarizer()
    from app.stubs.llm_stub import StubArticleSummarizer
    return StubArticleSummarizer()

def get_notifier() -> PushNotifier:
    if EXTERNAL_MODE == "real":
        from app.clients.notifier_real import RealPushNotifier
        return RealPushNotifier()
    from app.stubs.notifier_stub import StubPushNotifier
    return StubPushNotifier()
