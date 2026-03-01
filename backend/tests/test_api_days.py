"""TEST: days API のソート順とフォールバック動作（外部依存ゼロ）"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_article_doc(aid: str, happy_score: float, published_at: str) -> MagicMock:
    doc = MagicMock()
    doc.exists = True
    doc.to_dict.return_value = {
        "title": f"Article {aid}",
        "happy_score": happy_score,
        "published_at": published_at,
        "source_name": "Test",
        "summary_3lines": "a\nb\nc",
        "original_url": "https://example.com",
        "source_url": "",
        "thumbnail_url": None,
        "tags": [],
        "category": "mixed",
        "language": "en",
        "day_key": "2026-03-01",
        "collected_at": "2026-03-01T00:00:00+00:00",
    }
    return doc


def _make_day_doc(article_ids: list[str]) -> MagicMock:
    doc = MagicMock()
    doc.exists = True
    doc.to_dict.return_value = {
        "day_key": "2026-03-01",
        "article_ids": article_ids,
        "published_at": "2026-03-01T06:00:00+00:00",
        "stats": {"count": len(article_ids)},
    }
    return doc


def _make_missing_doc() -> MagicMock:
    doc = MagicMock()
    doc.exists = False
    return doc


class TestArticlesSortOrder:
    @pytest.mark.asyncio
    async def test_sorted_by_happy_score_desc(self):
        """happy_score 降順でソートされること"""
        articles = {
            "a1": _make_article_doc("a1", happy_score=0.5, published_at="2026-03-01T01:00:00+00:00"),
            "a2": _make_article_doc("a2", happy_score=0.95, published_at="2026-03-01T02:00:00+00:00"),
            "a3": _make_article_doc("a3", happy_score=0.75, published_at="2026-03-01T03:00:00+00:00"),
        }
        day_doc = _make_day_doc(["a1", "a2", "a3"])

        mock_db = MagicMock()

        async def mock_day_get():
            return day_doc

        async def mock_article_get(aid):
            return articles[aid]

        day_ref = MagicMock()
        day_ref.get = AsyncMock(return_value=day_doc)
        article_refs = {}
        for aid, doc in articles.items():
            ref = MagicMock()
            ref.get = AsyncMock(return_value=doc)
            article_refs[aid] = ref

        def collection_side_effect(name):
            coll = MagicMock()
            if name == "days":
                def document_days(key):
                    return day_ref
                coll.document = document_days
            elif name == "articles":
                def document_articles(aid):
                    return article_refs[aid]
                coll.document = document_articles
            return coll

        mock_db.collection = collection_side_effect

        with patch("app.api.v1.days.get_db", return_value=mock_db), \
             patch("app.api.v1.days.today_jst", return_value="2026-03-01"):
            from httpx import AsyncClient, ASGITransport
            import os
            os.environ["EXTERNAL_MODE"] = "stub"
            os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
            from app.main import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/v1/days/2026-03-01/articles")

        assert resp.status_code == 200
        data = resp.json()
        scores = [a["happy_score"] for a in data["articles"]]
        assert scores == sorted(scores, reverse=True), f"Expected desc sort, got: {scores}"

    @pytest.mark.asyncio
    async def test_same_score_sorted_by_published_at_desc(self):
        """happy_score が同じ場合 published_at 降順（新しい記事が先）"""
        articles = {
            "a1": _make_article_doc("a1", happy_score=0.8, published_at="2026-03-01T01:00:00+00:00"),
            "a2": _make_article_doc("a2", happy_score=0.8, published_at="2026-03-01T03:00:00+00:00"),
        }
        day_doc = _make_day_doc(["a1", "a2"])

        day_ref = MagicMock()
        day_ref.get = AsyncMock(return_value=day_doc)
        article_refs = {aid: MagicMock() for aid in articles}
        for aid, doc in articles.items():
            article_refs[aid].get = AsyncMock(return_value=doc)

        mock_db = MagicMock()

        def collection_side_effect(name):
            coll = MagicMock()
            if name == "days":
                coll.document = lambda key: day_ref
            elif name == "articles":
                coll.document = lambda aid: article_refs[aid]
            return coll

        mock_db.collection = collection_side_effect

        with patch("app.api.v1.days.get_db", return_value=mock_db), \
             patch("app.api.v1.days.today_jst", return_value="2026-03-01"):
            from httpx import AsyncClient, ASGITransport
            import os
            os.environ["EXTERNAL_MODE"] = "stub"
            from app.main import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/v1/days/2026-03-01/articles")

        assert resp.status_code == 200
        data = resp.json()
        dates = [a["published_at"] for a in data["articles"]]
        assert dates == sorted(dates, reverse=True), f"Expected newer first, got: {dates}"


class TestDaysFallback:
    @pytest.mark.asyncio
    async def test_missing_day_returns_fallback_or_404(self):
        """存在しない day_key でリクエストした場合、500 にならないこと（200 or 404）"""
        missing_doc = _make_missing_doc()

        mock_db = MagicMock()

        def collection_side_effect(name):
            coll = MagicMock()
            if name == "days":
                coll.document = lambda key: MagicMock(get=AsyncMock(return_value=missing_doc))
            return coll

        mock_db.collection = collection_side_effect

        with patch("app.api.v1.days.get_db", return_value=mock_db), \
             patch("app.api.v1.days.today_jst", return_value="2026-01-01"):
            from httpx import AsyncClient, ASGITransport
            import os
            os.environ["EXTERNAL_MODE"] = "stub"
            from app.main import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/v1/days/2026-01-01/articles")

        assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"
