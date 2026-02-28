from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.v1 import days, articles, users
import logging
import time
import uuid
from collections import defaultdict

logger = logging.getLogger("happynews")

app = FastAPI(title="HappyNews API", version="1.0.0")
app.include_router(days.router, prefix="/v1")
app.include_router(articles.router, prefix="/v1")
app.include_router(users.router, prefix="/v1")

# BE-028: 簡易レート制限（UID/IP ごとに 1 分間 60 リクエスト）
_rate_limit_window = 60.0
_rate_limit_max = 60
_rate_counts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key: str) -> bool:
    """True: 制限内, False: 制限超過"""
    now = time.monotonic()
    window_start = now - _rate_limit_window
    times = _rate_counts[key]
    # 古いエントリを削除
    _rate_counts[key] = [t for t in times if t > window_start]
    if len(_rate_counts[key]) >= _rate_limit_max:
        return False
    _rate_counts[key].append(now)
    return True


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.monotonic()

    # レート制限チェック（/health は除外）
    if request.url.path != "/health":
        uid = request.headers.get("X-Uid", "")
        client_ip = request.client.host if request.client else "unknown"
        rate_key = uid if uid else client_ip
        if not _check_rate_limit(rate_key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"X-Request-Id": request_id, "Retry-After": "60"},
            )

    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Request-Id"] = request_id
    logger.info(f"request_id={request_id} method={request.method} path={request.url.path} status={response.status_code} duration_ms={duration_ms}")
    return response


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    return {"status": "ok"}
