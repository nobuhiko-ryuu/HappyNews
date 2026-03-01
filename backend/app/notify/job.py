"""
BE-050: FCM送信サービス
BE-051: Scheduler毎時起動対応
BE-052: 対象ユーザー抽出（enabled=true & notification_time == current_hour）
BE-053: ペイロード（DeepLink→Today）
BE-054: 送信ログ
BE-055: 軽量リトライ
"""
from __future__ import annotations
import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from app.container import get_notifier
from app.ports.notifier import NotificationPayload
from app.db.firestore_client import get_db
from app.utils.day_key import today_jst

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("happynews.notify.job")

JST = timezone(timedelta(hours=9))
_MAX_RETRY = 2
_BATCH_SIZE = 500  # FCM multicast 上限


async def run_notify_job(hour: int | None = None) -> dict:
    """
    毎時起動のエントリポイント。
    hour: 0-23（省略時はJST現在時刻）
    """
    run_id = str(uuid.uuid4())[:8]
    start = time.monotonic()
    if hour is None:
        hour = datetime.now(JST).hour
    logger.info(f"[{run_id}] Notify job starting for hour={hour}")

    result = {
        "run_id": run_id,
        "hour": hour,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "targeted": 0,
        "sent": 0,
        "failed": 0,
        "errors": [],
    }

    try:
        db = get_db()
        notifier = get_notifier()

        # BE-052: 対象ユーザー抽出
        tokens = await _extract_target_tokens(db, hour)
        result["targeted"] = len(tokens)

        if not tokens:
            logger.info(f"[{run_id}] No targets for hour={hour}")
            return result

        # BE-053: ペイロード（DeepLink → Today）
        day_key = today_jst()
        payload = NotificationPayload(
            title="ハッピーニュース 🌟",
            body="今日のハッピーニュースが届きました！",
            day_key=day_key,
            deeplink="happynews://today",
        )

        # BE-055: バッチ送信 + 軽量リトライ
        sent = 0
        failed = 0
        for i in range(0, len(tokens), _BATCH_SIZE):
            batch_tokens = tokens[i:i + _BATCH_SIZE]
            for attempt in range(_MAX_RETRY + 1):
                try:
                    notify_result = await notifier.send_multicast(batch_tokens, payload)
                    sent += notify_result["success"]
                    failed += notify_result["failure"]
                    break
                except Exception as e:
                    if attempt == _MAX_RETRY:
                        failed += len(batch_tokens)
                        result["errors"].append(str(e))
                        logger.error(f"[{run_id}] Batch failed after {_MAX_RETRY} retries: {e}")
                    else:
                        await asyncio.sleep(2 ** attempt)

        result["sent"] = sent
        result["failed"] = failed
        elapsed = time.monotonic() - start
        result["elapsed_seconds"] = round(elapsed, 1)
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[{run_id}] Notify done: sent={sent} failed={failed} in {elapsed:.1f}s")

        # BE-054: 送信ログを Firestore に保存
        await _save_notify_log(db, result)

    except Exception as e:
        logger.error(f"[{run_id}] Notify job failed: {e}", exc_info=True)
        result["errors"].append(str(e))

    return result


async def _extract_target_tokens(db, hour: int) -> list[str]:
    """
    users コレクションから notification_enabled=True かつ
    notification_time == hour のユーザーの FCM トークンを取得。
    """
    tokens = []
    query = (
        db.collection("users")
        .where("notification_enabled", "==", True)
        .where("notification_time", "==", hour)
    )
    async for doc in query.stream():
        data = doc.to_dict()
        token = data.get("fcm_token")
        if token:
            tokens.append(token)
    logger.info(f"Extracted {len(tokens)} tokens for hour={hour}")
    return tokens


async def _save_notify_log(db, result: dict) -> None:
    """BE-054: 送信ログを notify_logs コレクションに保存"""
    try:
        log_id = result["run_id"]
        await db.collection("notify_logs").document(log_id).set(result)
    except Exception as e:
        logger.warning(f"Failed to save notify log: {e}")


def main():
    """Cloud Run Job エントリポイント（毎時起動）"""
    hour_env = os.getenv("NOTIFY_HOUR")
    hour = int(hour_env) if hour_env else None
    asyncio.run(run_notify_job(hour=hour))


if __name__ == "__main__":
    main()
