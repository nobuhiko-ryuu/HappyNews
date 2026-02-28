from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.db.firestore_client import get_db

router = APIRouter(tags=["articles"])


@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    """記事詳細（要約・タグ・出典URL）"""
    db = get_db()
    doc = await db.collection("articles").document(article_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"id": article_id, **doc.to_dict()}
