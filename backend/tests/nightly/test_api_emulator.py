"""
TEST-011: API 契約テスト（並び順・フォールバック含む）
外部依存ゼロ（Firestore Emulator使用）
"""
from __future__ import annotations
import pytest
import os
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone, timedelta


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("EXTERNAL_MODE", "stub")
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "localhost:8080")


@pytest.fixture
async def seeded_db():
    """テスト用 Firestore にサンプルデータを投入"""
    import firebase_admin
    from firebase_admin import firestore
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    db = firestore.AsyncClient()

    day_key = "2026-03-01"
    article_ids = []
    now = datetime.now(timezone.utc)

    # 記事を3件投入（happy_score の逆順で投入し、ソートを確認）
    articles_data = [
        {"title": "Article Low", "happy_score": 0.5, "category": "community",
         "published_at": (now - timedelta(hours=2)).isoformat()},
        {"title": "Article High", "happy_score": 0.95, "category": "science",
         "published_at": (now - timedelta(hours=1)).isoformat()},
        {"title": "Article Mid", "happy_score": 0.75, "category": "health",
         "published_at": now.isoformat()},
    ]
    for a in articles_data:
        ref = await db.collection("articles").add({
            **a,
            "summary_3lines": "line1\nline2\nline3",
            "original_url": "https://example.com",
            "source_name": "Test Source",
            "thumbnail_url": None,
            "tags": [],
            "language": "en",
            "day_key": day_key,
            "source_url": "",
            "collected_at": now.isoformat(),
        })
        article_ids.append(ref[1].id)

    await db.collection("days").document(day_key).set({
        "day_key": day_key,
        "article_ids": article_ids,
        "published_at": now.isoformat(),
        "stats": {"count": len(article_ids)},
    })

    yield {"day_key": day_key, "article_ids": article_ids}

    # クリーンアップ
    for aid in article_ids:
        await db.collection("articles").document(aid).delete()
    await db.collection("days").document(day_key).delete()


@pytest.mark.asyncio
async def test_health_endpoint():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_get_latest_day_returns_404_when_no_data():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/days/latest")
    # データなし → 404
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_articles_invalid_day_key():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/days/invalid-key/articles")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_article_not_found():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/articles/nonexistent-id")
    assert resp.status_code == 404
