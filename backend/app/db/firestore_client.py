from __future__ import annotations
import os
import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1.async_client import AsyncClient

_db: AsyncClient | None = None


def get_db() -> AsyncClient:
    global _db
    if _db is None:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _db = firestore.AsyncClient()
    return _db
