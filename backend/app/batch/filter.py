"""BE-036: Rule Filter - NGワード/NGソース/NGカテゴリでフィルタリング"""
from __future__ import annotations
import logging
import re

logger = logging.getLogger("happynews.batch.filter")


def apply_rule_filter(
    candidates: list[dict],
    ng_words: list[str],
    ng_source_ids: list[str],
    ng_categories: list[str],
) -> list[dict]:
    """
    ルールベースのフィルタリングを適用。
    rule_filtered=True のものは除外し、理由を記録する。
    """
    filtered = []
    for c in candidates:
        reasons = []

        # NGソース
        if c.get("source_id") in ng_source_ids:
            reasons.append(f"ng_source:{c['source_id']}")

        # NGワード（タイトル + 抜粋）
        text = f"{c.get('title', '')} {c.get('excerpt', '')}".lower()
        for word in ng_words:
            if word.lower() in text:
                reasons.append(f"ng_word:{word}")
                break

        if reasons:
            c = dict(c)
            c["rule_filtered"] = True
            c["rule_filter_reasons"] = reasons
            logger.debug(f"Filtered: {c.get('title', '')[:50]} - {reasons}")
        filtered.append(c)

    passed = [c for c in filtered if not c["rule_filtered"]]
    logger.info(f"Rule filter: {len(candidates)} -> {len(passed)} passed ({len(candidates) - len(passed)} filtered)")
    return filtered  # フィルタ済みフラグ付きで全件返す（runs記録用）
