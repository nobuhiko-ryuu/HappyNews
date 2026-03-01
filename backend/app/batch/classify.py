"""BE-037: LLM軽判定 - happy_score/category/tags/is_ng を付与"""
from __future__ import annotations
import asyncio
import logging
from app.ports.llm import ArticleClassifier, ClassifyResult

logger = logging.getLogger("happynews.batch.classify")

_CONCURRENCY = 5  # 同時リクエスト数上限


async def classify_candidates(
    candidates: list[dict],
    classifier: ArticleClassifier,
    db=None,
) -> list[dict]:
    """
    rule_filtered=False の候補に対して LLM 軽判定を実行。
    並列処理（上限 _CONCURRENCY）。
    """
    to_classify = [c for c in candidates if not c.get("rule_filtered", False)]
    sem = asyncio.Semaphore(_CONCURRENCY)
    results = list(candidates)  # 元リストをコピー
    idx_map = {id(c): i for i, c in enumerate(candidates)}

    async def _classify_one(c: dict) -> None:
        async with sem:
            try:
                result: ClassifyResult = await classifier.classify(
                    title=c.get("title", ""),
                    excerpt=c.get("excerpt", ""),
                    language=c.get("lang", "en"),
                )
                idx = idx_map[id(c)]
                updated = dict(c) | {
                    "llm_happy_score": result.happy_score,
                    "llm_category": result.category,
                    "llm_tags": result.tags,
                    "llm_is_ng": result.is_ng,
                }
                results[idx] = updated
                # Firestore に分類結果を書き戻す
                if db is not None:
                    candidate_id = c.get("_candidate_id")
                    if candidate_id:
                        ref = db.collection("candidates").document(candidate_id)
                        await ref.set(
                            {
                                "llm_happy_score": result.happy_score,
                                "llm_category": result.category,
                                "llm_tags": result.tags,
                                "llm_is_ng": result.is_ng,
                            },
                            merge=True,
                        )
            except Exception as e:
                logger.warning(f"Classify failed for '{c.get('title', '')[:40]}': {e}")

    await asyncio.gather(*[_classify_one(c) for c in to_classify])
    logger.info(f"Classified {len(to_classify)} candidates")
    return results
