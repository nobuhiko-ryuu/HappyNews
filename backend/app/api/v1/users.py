from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, field_validator
from typing import Optional
from app.db.firestore_client import get_db

router = APIRouter(tags=["users"])


class SettingsUpdate(BaseModel):
    notification_enabled: Optional[bool] = None
    notification_time: Optional[int] = None      # 0-23 (HH:00)
    mute_words: Optional[list[str]] = None
    fcm_token: Optional[str] = None

    @field_validator("notification_time")
    @classmethod
    def validate_hour(cls, v):
        if v is not None and not (0 <= v <= 23):
            raise ValueError("notification_time must be 0-23")
        return v


def _require_uid(x_uid: str = Header(..., alias="X-Uid")) -> str:
    if not x_uid:
        raise HTTPException(status_code=401, detail="X-Uid header required")
    return x_uid


@router.get("/users/me/bookmarks")
async def get_bookmarks(uid: str = Header(..., alias="X-Uid")):
    db = get_db()
    docs = db.collection("users").document(uid).collection("bookmarks").stream()
    bookmarks = []
    async for doc in docs:
        bookmarks.append({"id": doc.id, **doc.to_dict()})
    bookmarks.sort(key=lambda b: b.get("saved_at", ""), reverse=True)
    return {"bookmarks": bookmarks}


@router.post("/users/me/bookmarks/{article_id}", status_code=201)
async def add_bookmark(article_id: str, uid: str = Header(..., alias="X-Uid")):
    db = get_db()
    article = await db.collection("articles").document(article_id).get()
    if not article.exists:
        raise HTTPException(status_code=404, detail="Article not found")
    saved_at = datetime.now(timezone.utc).isoformat()
    await (db.collection("users").document(uid)
             .collection("bookmarks").document(article_id)
             .set({"article_id": article_id, "saved_at": saved_at, **article.to_dict()}))
    return {"status": "saved"}


@router.delete("/users/me/bookmarks/{article_id}", status_code=204)
async def remove_bookmark(article_id: str, uid: str = Header(..., alias="X-Uid")):
    db = get_db()
    await (db.collection("users").document(uid)
             .collection("bookmarks").document(article_id).delete())


@router.put("/users/me/settings")
async def update_settings(settings: SettingsUpdate, uid: str = Header(..., alias="X-Uid")):
    db = get_db()
    update = {k: v for k, v in settings.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    await db.collection("users").document(uid).set(update, merge=True)
    return {"status": "updated"}
