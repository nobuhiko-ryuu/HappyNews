"""TEST: バッチ統合テスト（20本/日・外部依存ゼロ）"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_firestore_mock():
    """Firestore DB の最小モックを返す"""
    mock_db = MagicMock()

    # configs/global → デフォルト設定
    config_doc = MagicMock()
    config_doc.exists = True
    config_doc.to_dict.return_value = {
        "candidate_target_per_day": 200,
        "candidate_hard_limit_per_day": 500,
        "publish_count_per_day": 20,
        "per_category_max": {},
        "ng_words": [],
        "ng_source_ids": [],
        "ng_categories": [],
        "summary_rule": {},
    }

    # sources コレクション（1件のソース）
    source_doc = MagicMock()
    source_doc.id = "src1"
    source_doc.to_dict.return_value = {
        "name": "Test Source",
        "feed_url": "https://example.com/feed",
        "enabled": True,
        "priority": 1,
        "language_hint": "en",
        "homepage_url": "https://example.com",
    }

    async def _sources_stream():
        yield source_doc

    # days/{day_key} の存在確認
    missing_day_doc = MagicMock()
    missing_day_doc.exists = False

    # バッチ書き込みモック
    batch_mock = MagicMock()
    batch_mock.set = MagicMock()
    batch_mock.commit = AsyncMock()

    def _collection(name):
        coll = MagicMock()
        if name == "configs":
            coll.document.return_value.get = AsyncMock(return_value=config_doc)
        elif name == "sources":
            query = MagicMock()
            query.where.return_value.order_by.return_value.stream = _sources_stream
            coll.where.return_value.order_by.return_value = query.where.return_value.order_by.return_value
            coll.where = query.where
        elif name == "candidates":
            coll.document.return_value.set = AsyncMock()
        elif name == "articles":
            coll.document.return_value.set = AsyncMock()
        elif name == "days":
            coll.document.return_value.get = AsyncMock(return_value=missing_day_doc)
            coll.document.return_value.set = AsyncMock()
        elif name == "runs":
            coll.document.return_value.set = AsyncMock()
        return coll

    mock_db.collection = _collection
    mock_db.batch.return_value = batch_mock
    return mock_db


class TestBatchIntegration:
    @pytest.mark.asyncio
    async def test_batch_publishes_20_articles(self):
        """stub モードでバッチを実行し 20 本の記事が publish されること"""
        mock_db = _make_firestore_mock()

        with patch("app.batch.job.get_db", return_value=mock_db), \
             patch("app.batch.collect.get_db", return_value=mock_db), \
             patch("app.batch.publish.get_db", return_value=mock_db), \
             patch("app.container.get_fetcher") as mock_get_fetcher, \
             patch("app.container.get_classifier") as mock_get_classifier, \
             patch("app.container.get_summarizer") as mock_get_summarizer:
            import os
            os.environ["EXTERNAL_MODE"] = "stub"

            from app.stubs.fetcher_stub import StubArticleFetcher
            from app.stubs.llm_stub import StubArticleClassifier, StubArticleSummarizer
            mock_get_fetcher.return_value = StubArticleFetcher()
            mock_get_classifier.return_value = StubArticleClassifier()
            mock_get_summarizer.return_value = StubArticleSummarizer()

            from app.batch.job import run_batch
            result = await run_batch(day_key="2026-03-01", dry_run=False)

        assert result["status"] == "success", f"Batch failed: {result.get('errors')}"
        assert result["counts"]["published"] == 20, \
            f"Expected 20 published, got {result['counts']['published']}"

    @pytest.mark.asyncio
    async def test_batch_dry_run_does_not_write(self):
        """dry_run=True の場合、Firestore に書き込まないこと"""
        mock_db = _make_firestore_mock()

        with patch("app.batch.job.get_db", return_value=mock_db), \
             patch("app.batch.collect.get_db", return_value=mock_db), \
             patch("app.batch.publish.get_db", return_value=mock_db), \
             patch("app.container.get_fetcher") as mock_get_fetcher, \
             patch("app.container.get_classifier") as mock_get_classifier, \
             patch("app.container.get_summarizer") as mock_get_summarizer:
            import os
            os.environ["EXTERNAL_MODE"] = "stub"

            from app.stubs.fetcher_stub import StubArticleFetcher
            from app.stubs.llm_stub import StubArticleClassifier, StubArticleSummarizer
            mock_get_fetcher.return_value = StubArticleFetcher()
            mock_get_classifier.return_value = StubArticleClassifier()
            mock_get_summarizer.return_value = StubArticleSummarizer()

            from app.batch.job import run_batch
            result = await run_batch(day_key="2026-03-01", dry_run=True)

        assert result["status"] == "success"
        assert result["counts"]["published"] == 20
        # dry_run では articles コレクションへの set が呼ばれない
        # （publish_articles が "dry-N" を返すだけ）
        articles_coll = mock_db.collection("articles")
        articles_coll.document.return_value.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_idempotent_candidate_ids(self):
        """同じ URL から収集された候補は同一 _candidate_id を持つこと"""
        from app.batch.collect import _candidate_doc_id
        url = "https://example.com/article-0"
        source_id = "src1"
        id1 = _candidate_doc_id(url, source_id)
        id2 = _candidate_doc_id(url, source_id)
        assert id1 == id2
        assert len(id1) == 32  # MD5 hex

    @pytest.mark.asyncio
    async def test_candidate_has_ttl_and_thumbnail(self):
        """収集された候補に ttl_delete_at と thumbnail_url が含まれること"""
        mock_db = _make_firestore_mock()

        with patch("app.batch.collect.get_db", return_value=mock_db), \
             patch("app.container.get_fetcher") as mock_get_fetcher:
            import os
            os.environ["EXTERNAL_MODE"] = "stub"

            from app.stubs.fetcher_stub import StubArticleFetcher
            mock_get_fetcher.return_value = StubArticleFetcher()

            from app.batch.collect import collect_candidates
            from app.stubs.fetcher_stub import StubArticleFetcher
            candidates = await collect_candidates(
                StubArticleFetcher(), "2026-03-01", target=5, dry_run=True
            )

        assert len(candidates) > 0
        for c in candidates:
            assert "ttl_delete_at" in c, "Missing ttl_delete_at"
            assert "_candidate_id" in c, "Missing _candidate_id"
            assert "thumbnail_url" in c, "Missing thumbnail_url"
            assert "source_url" in c, "Missing source_url"
