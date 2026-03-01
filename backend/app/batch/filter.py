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
    result = []
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

        updated = dict(c)
        if reasons:
            updated["rule_filtered"] = True
            updated["rule_filter_reasons"] = reasons
            logger.debug(f"Filtered: {updated.get('title', '')[:50]} - {reasons}")
        else:
            updated["rule_filtered"] = False
            updated["rule_filter_reasons"] = []
        result.append(updated)

    passed = [c for c in result if not c["rule_filtered"]]
    logger.info(f"Rule filter: {len(candidates)} -> {len(passed)} passed ({len(candidates) - len(passed)} filtered)")
    return result  # フィルタ済みフラグ付きで全件返す（runs記録用）


async def write_filter_results(db, candidates: list[dict]) -> None:
    """フィルタ結果を Firestore candidates に merge 書き込み"""
    batch = db.batch()
    count = 0
    for i, c in enumerate(candidates):
        candidate_id = c.get("_candidate_id")
        if not candidate_id:
            continue
        ref = db.collection("candidates").document(candidate_id)
        batch.set(
            ref,
            {
                "rule_filtered": c.get("rule_filtered", False),
                "rule_filter_reasons": c.get("rule_filter_reasons", []),
            },
            merge=True,
        )
        count += 1
        if count % 499 == 0:
            await batch.commit()
            batch = db.batch()
    await batch.commit()
    logger.info(f"write_filter_results: merged {count} candidates")
