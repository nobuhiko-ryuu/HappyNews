from __future__ import annotations
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.db.firestore_client import get_db
from app.utils.day_key import today_jst, is_valid_day_key

router = APIRouter(tags=["days"])
JST = timezone(timedelta(hours=9))
FALLBACK_MAX_DAYS = 7


async def _find_latest_day_key(db) -> str | None:
    """最新の掲載日を最大 FALLBACK_MAX_DAYS 日遡って探す"""
    now = datetime.now(JST)
    for i in range(FALLBACK_MAX_DAYS):
        key = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        doc = await db.collection("days").document(key).get()
        if doc.exists:
            return key
    return None


@router.get("/days/latest")
async def get_latest():
    """最新の掲載日を返す（最大7日フォールバック）"""
    db = get_db()
    key = await _find_latest_day_key(db)
    if key is None:
        raise HTTPException(status_code=404, detail="No published day found within 7 days")
    return {"day_key": key}


@router.get("/days/{day_key}/articles")
async def get_articles_by_day(day_key: str):
    """指定日の掲載記事一覧（happy_score desc → published_at desc）"""
    if not is_valid_day_key(day_key):
        raise HTTPException(status_code=400, detail="Invalid day_key format. Use YYYY-MM-DD")

    db = get_db()
    day_doc = await db.collection("days").document(day_key).get()

    # 当日0件の場合はフォールバック
    if not day_doc.exists:
        fallback_key = await _find_latest_day_key(db)
        if fallback_key is None:
            raise HTTPException(status_code=404, detail="No articles found")
        day_key = fallback_key
        day_doc = await db.collection("days").document(day_key).get()

    data = day_doc.to_dict()
    article_ids: list[str] = data.get("article_ids", [])

    articles = []
    for aid in article_ids:
        adoc = await db.collection("articles").document(aid).get()
        if adoc.exists:
            articles.append({"id": aid, **adoc.to_dict()})

    # ソート: happy_score desc → published_at desc
    articles.sort(
        key=lambda a: (float(a.get("happy_score", 0.0)), a.get("published_at") or ""),
        reverse=True,
    )

    # Cache-Control: 当日は短TTL、過去日は長TTL
    is_today = (day_key == today_jst())
    cache_sec = 300 if is_today else 86400
    response = JSONResponse(content={"day_key": day_key, "articles": articles})
    response.headers["Cache-Control"] = f"public, max-age={cache_sec}"
    return response
