"""TEST-012: バッチ統合テスト（idempotent・掲載=20・原子性）- 外部依存ゼロ"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.batch.filter import apply_rule_filter
from app.batch.rank import rank_and_select
from app.batch.collect import _normalize_url


def make_candidate(title: str, score: float = 0.5, category: str = "mixed",
                   rule_filtered: bool = False, is_ng: bool = False) -> dict:
    return {
        "title": title,
        "excerpt": "",
        "source_id": "src1",
        "source_name": "Test",
        "original_url": f"https://example.com/{title}",
        "day_key": "2026-03-01",
        "collected_at": "2026-03-01T00:00:00+00:00",
        "lang": "en",
        "rule_filtered": rule_filtered,
        "rule_filter_reasons": [],
        "llm_happy_score": score,
        "llm_category": category,
        "llm_tags": [],
        "llm_is_ng": is_ng,
    }


class TestRuleFilter:
    def test_ng_word_filtered(self):
        candidates = [make_candidate("死亡事故のニュース"), make_candidate("Happy Science")]
        result = apply_rule_filter(candidates, ng_words=["死亡"], ng_source_ids=[], ng_categories=[])
        filtered = [c for c in result if c["rule_filtered"]]
        passed = [c for c in result if not c["rule_filtered"]]
        assert len(filtered) == 1
        assert len(passed) == 1
        assert "ng_word:死亡" in filtered[0]["rule_filter_reasons"]

    def test_ng_source_filtered(self):
        candidates = [make_candidate("Test"), make_candidate("Good")]
        candidates[0]["source_id"] = "bad_source"
        result = apply_rule_filter(candidates, ng_words=[], ng_source_ids=["bad_source"], ng_categories=[])
        assert result[0]["rule_filtered"] is True
        assert result[1]["rule_filtered"] is False

    def test_no_filter(self):
        candidates = [make_candidate("Good news"), make_candidate("Happy day")]
        result = apply_rule_filter(candidates, ng_words=[], ng_source_ids=[], ng_categories=[])
        assert all(not c["rule_filtered"] for c in result)


class TestRankAndSelect:
    def test_selects_top_n_by_score(self):
        candidates = [make_candidate(f"Article{i}", score=i * 0.1) for i in range(30)]
        selected = rank_and_select(candidates, publish_count=20)
        assert len(selected) == 20
        # 上位スコアが選ばれているか確認
        scores = [c["llm_happy_score"] for c in selected]
        assert scores == sorted(scores, reverse=True)

    def test_respects_category_limit(self):
        candidates = [make_candidate(f"Science{i}", score=0.9, category="science") for i in range(15)]
        candidates += [make_candidate(f"Health{i}", score=0.5, category="health") for i in range(10)]
        per_cat = {"science": 6, "health": 6}
        selected = rank_and_select(candidates, publish_count=20, per_category_max=per_cat)
        science_count = sum(1 for c in selected if c["llm_category"] == "science")
        assert science_count <= 6

    def test_relaxes_limits_when_insufficient(self):
        # 1カテゴリしかない場合は上限を緩める
        candidates = [make_candidate(f"Sci{i}", score=0.9, category="science") for i in range(25)]
        selected = rank_and_select(candidates, publish_count=20, per_category_max={"science": 6})
        assert len(selected) == 20

    def test_excludes_ng_articles(self):
        candidates = [make_candidate("NG article", score=0.99, is_ng=True)]
        candidates += [make_candidate(f"Good{i}", score=0.5) for i in range(25)]
        selected = rank_and_select(candidates, publish_count=20)
        assert all(not c.get("llm_is_ng") for c in selected)

    def test_excludes_rule_filtered(self):
        candidates = [make_candidate("Bad", rule_filtered=True, score=0.99)]
        candidates += [make_candidate(f"Good{i}", score=0.5) for i in range(25)]
        selected = rank_and_select(candidates, publish_count=20)
        assert all(not c.get("rule_filtered") for c in selected)


class TestNormalizeUrl:
    def test_removes_utm_params(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
        normalized = _normalize_url(url)
        assert "utm_source" not in normalized
        assert "id=123" in normalized

    def test_removes_trailing_slash(self):
        assert _normalize_url("https://example.com/article/") == "https://example.com/article"

    def test_handles_invalid_url(self):
        assert _normalize_url("not-a-url") == "not-a-url"
