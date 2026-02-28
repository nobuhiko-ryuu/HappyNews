import os
from app.ports.fetcher import ArticleFetcher
from app.ports.llm import ArticleClassifier, ArticleSummarizer
from app.ports.notifier import PushNotifier


def _get_mode() -> str:
    mode = os.getenv("EXTERNAL_MODE", "stub")
    if mode not in ("stub", "real"):
        raise ValueError(f"Invalid EXTERNAL_MODE: {mode!r}. Must be 'stub' or 'real'.")
    return mode


def get_fetcher() -> ArticleFetcher:
    if _get_mode() == "real":
        from app.clients.fetcher_real import RealArticleFetcher
        return RealArticleFetcher()
    from app.stubs.fetcher_stub import StubArticleFetcher
    return StubArticleFetcher()


def get_classifier() -> ArticleClassifier:
    if _get_mode() == "real":
        from app.clients.llm_real import RealArticleClassifier
        return RealArticleClassifier()
    from app.stubs.llm_stub import StubArticleClassifier
    return StubArticleClassifier()


def get_summarizer() -> ArticleSummarizer:
    if _get_mode() == "real":
        from app.clients.llm_real import RealArticleSummarizer
        return RealArticleSummarizer()
    from app.stubs.llm_stub import StubArticleSummarizer
    return StubArticleSummarizer()


def get_notifier() -> PushNotifier:
    if _get_mode() == "real":
        from app.clients.notifier_real import RealPushNotifier
        return RealPushNotifier()
    from app.stubs.notifier_stub import StubPushNotifier
    return StubPushNotifier()
