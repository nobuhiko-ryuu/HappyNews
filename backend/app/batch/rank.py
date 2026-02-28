"""BE-038: Rank & Select - カテゴリ上限を考慮して上位20本を選出"""
from __future__ import annotations
import logging

logger = logging.getLogger("happynews.batch.rank")


def rank_and_select(
    candidates: list[dict],
    publish_count: int = 20,
    per_category_max: dict | None = None,
) -> list[dict]:
    """
    happy_score 降順で走査し、per_category_max を超える候補をスキップ。
    publish_count 本揃うまで選出。
    揃わない場合はカテゴリ上限を緩めて再選出。
    """
    per_category_max = per_category_max or {}

    def _select(candidates_sorted: list[dict], limits: dict) -> list[dict]:
        selected = []
        category_count: dict[str, int] = {}
        for c in candidates_sorted:
            if len(selected) >= publish_count:
                break
            cat = c.get("llm_category", "mixed") or "mixed"
            limit = limits.get(cat, publish_count)  # デフォルトは上限なし
            if category_count.get(cat, 0) >= limit:
                continue
            selected.append(c)
            category_count[cat] = category_count.get(cat, 0) + 1
        return selected

    # rule_filtered=False かつ llm_is_ng=False のみ対象
    eligible = [c for c in candidates
                if not c.get("rule_filtered", False) and not c.get("llm_is_ng", False)]
    eligible.sort(key=lambda c: -c.get("llm_happy_score", 0.0))

    selected = _select(eligible, per_category_max)

    # 揃わない場合: カテゴリ上限を緩めて再選出（上限倍増をループ）
    # カテゴリが複数存在する場合は上限を緩めない（多様性を優先）
    distinct_eligible_cats = {c.get("llm_category", "mixed") or "mixed" for c in eligible}
    if len(selected) < publish_count and per_category_max and len(distinct_eligible_cats) <= 1:
        logger.warning(f"Only {len(selected)}/{publish_count} selected with category limits, relaxing...")
        relaxed = {k: v * 2 for k, v in per_category_max.items()}
        prev_count = len(selected)
        while len(selected) < min(publish_count, len(eligible)):
            new_selected = _select(eligible, relaxed)
            if len(new_selected) == prev_count:
                # これ以上改善しない場合は打ち切り
                break
            selected = new_selected
            prev_count = len(selected)
            relaxed = {k: v * 2 for k, v in relaxed.items()}

    logger.info(f"Selected {len(selected)}/{publish_count} articles from {len(eligible)} eligible")
    return selected
