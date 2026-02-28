"""BE-030: Cloud Run Job 雛形 - 日次バッチのエントリポイント"""
from __future__ import annotations
import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from app.batch.collect import collect_candidates
from app.batch.filter import apply_rule_filter
from app.batch.classify import classify_candidates
from app.batch.rank import rank_and_select
from app.batch.summarize import summarize_articles
from app.batch.publish import publish_articles
from app.container import get_fetcher, get_classifier, get_summarizer
from app.db.firestore_client import get_db
from app.utils.day_key import today_jst

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("happynews.batch.job")


async def run_batch(
    day_key: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    日次バッチのメイン処理（冪等）。
    day_key: 省略時は JST 当日
    dry_run: True の場合は Firestore に書き込まない
    """
    run_id = str(uuid.uuid4())[:8]
    start = time.monotonic()
    day_key = day_key or today_jst()
    logger.info(f"[{run_id}] Starting batch for {day_key} (dry_run={dry_run})")

    run_record = {
        "run_id": run_id,
        "day_key": day_key,
        "dry_run": dry_run,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "counts": {},
        "errors": [],
        "cost_estimates": {},
    }

    try:
        db = get_db()

        # configs/global を読み込む
        config_doc = await db.collection("configs").document("global").get()
        config = config_doc.to_dict() if config_doc.exists else {}
        target = config.get("candidate_target_per_day", 200)
        hard_limit = config.get("candidate_hard_limit_per_day", 500)
        publish_count = config.get("publish_count_per_day", 20)
        per_category_max = config.get("per_category_max", {})
        ng_words = config.get("ng_words", [])
        ng_source_ids = config.get("ng_source_ids", [])
        ng_categories = config.get("ng_categories", [])
        summary_rule = config.get("summary_rule", {})

        # 1. Collect
        fetcher = get_fetcher()
        candidates = await collect_candidates(fetcher, day_key, target, hard_limit, dry_run)
        run_record["counts"]["collected"] = len(candidates)

        # 2. Rule Filter
        candidates = apply_rule_filter(candidates, ng_words, ng_source_ids, ng_categories)
        passed = [c for c in candidates if not c.get("rule_filtered")]
        run_record["counts"]["after_rule_filter"] = len(passed)

        # 3. LLM Classify
        classifier = get_classifier()
        candidates = await classify_candidates(candidates, classifier)
        run_record["counts"]["classified"] = len([c for c in candidates if not c.get("rule_filtered")])

        # 4. Rank & Select
        selected = rank_and_select(candidates, publish_count, per_category_max)
        run_record["counts"]["selected"] = len(selected)

        # 5. LLM Summarize
        selected = await summarize_articles(selected, get_summarizer(), summary_rule)

        # 6. Publish
        article_ids = await publish_articles(day_key, selected, dry_run)
        run_record["counts"]["published"] = len(article_ids)

        elapsed = time.monotonic() - start
        run_record["status"] = "success"
        run_record["elapsed_seconds"] = round(elapsed, 1)
        run_record["finished_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[{run_id}] Batch completed in {elapsed:.1f}s: {len(article_ids)} articles published")

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error(f"[{run_id}] Batch failed: {e}", exc_info=True)
        run_record["status"] = "failed"
        run_record["errors"].append(str(e))
        run_record["elapsed_seconds"] = round(elapsed, 1)
        run_record["finished_at"] = datetime.now(timezone.utc).isoformat()

    finally:
        # runs/{run_id} に記録 (BE-042)
        if not dry_run:
            try:
                db = get_db()
                await db.collection("runs").document(run_id).set(run_record)
            except Exception as e:
                logger.error(f"Failed to save run record: {e}")

    return run_record


def main():
    """Cloud Run Job のエントリポイント"""
    day_key = os.getenv("DAY_KEY")
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    result = asyncio.run(run_batch(day_key=day_key, dry_run=dry_run))
    if result.get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
