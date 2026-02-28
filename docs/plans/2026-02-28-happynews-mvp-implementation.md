# HappyNews MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ハッピーなニュースを毎日20本自動配信するAndroidアプリ（MVP）を、3エージェント（Orchestrator / Backend / Android）で実装する。

**Architecture:** GCP/Firebase バックエンド（Cloud Run + Firestore + FCM）と Kotlin/Compose Android アプリ。Orchestrator が Phase 0 でインタフェース定義を確定し、Backend と Android が並列で M1〜M6 を進める。

**Tech Stack:**
- Backend: Python 3.11 / FastAPI / firebase-admin / feedparser / openai / Google Cloud Run
- Android: Kotlin / Jetpack Compose / Hilt / Retrofit / Room / Coil
- Infrastructure: Firestore / Firebase Auth / FCM / Cloud Scheduler / Secret Manager / GitHub Actions

---

## 前提・共通ルール

- **仕様の正**: `docs/` 以下のドキュメント（外部設計・アーキ設計・inputoutput_spec）が最優先
- **シークレット**: リポジトリにコミットしない（Secret Manager / `.env.local` / `.gitignore`）
- **CI が赤 → 最優先で復旧**
- **コミット**: 各タスク完了時。ブランチ命名 `feat/xxx` `fix/xxx` `chore/xxx` `docs/xxx`
- **Progress.md**: マイルストーン完了・ブロッカー発生・Token 80% 超過時に更新
- **ユーザー確認不要**: エージェントの判断で自律的に進める

---

## Phase 0：GitHub リポジトリ作成 + インタフェース定義【Orchestrator】

### Task 0-1: GitHub リポジトリ作成

**Files:**
- Create: `.gitignore`
- Create: `README.md`

**Step 1: GitHub リポジトリを作成**
```bash
gh repo create HappyNews --private --description "毎日ハッピーなニュースを20本届けるAndroidアプリ" --clone
cd HappyNews
```

**Step 2: プロジェクト基本構造を作成**
```
HappyNews/
├── backend/          # Python/FastAPI バックエンド
├── android/          # Kotlin/Compose Android アプリ
├── docs/             # 既存ドキュメント（コピー）
├── .github/
│   ├── workflows/
│   └── PULL_REQUEST_TEMPLATE.md
├── .gitignore
└── README.md
```

**Step 3: .gitignore を作成**
```
# Secrets
.env
.env.*
!.env.example
*.keystore
google-services.json
service-account*.json

# Python
__pycache__/
*.py[cod]
.venv/
dist/
*.egg-info/

# Android
android/.gradle/
android/local.properties
android/build/
android/app/build/
*.iml

# IDE
.idea/
.vscode/
*.DS_Store
```

**Step 4: docs/ を既存パスからコピーして commit**
```bash
cp -r /c/Users/my/claude_code/Projects/HappyNews/docs ./
git add .
git commit -m "chore: initial project structure"
git push -u origin main
```

---

### Task 0-2: TEST-001 External Clients インタフェース定義【Orchestrator】

**Files:**
- Create: `backend/app/ports/__init__.py`
- Create: `backend/app/ports/fetcher.py`
- Create: `backend/app/ports/llm.py`
- Create: `backend/app/ports/notifier.py`

**Step 1: fetcher.py（RSS収集インタフェース）**
```python
# backend/app/ports/fetcher.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class RawArticle:
    url: str
    title: str
    excerpt: str          # 数百文字まで（全文保存しない）
    published_at: Optional[datetime]
    source_id: str
    source_name: str
    thumbnail_url: Optional[str]
    language_hint: str = "unknown"

class ArticleFetcher(ABC):
    @abstractmethod
    async def fetch(self, feed_url: str, source_id: str, source_name: str, limit: int = 50) -> list[RawArticle]:
        """RSS/APIからRawArticleリストを取得する"""
        ...
```

**Step 2: llm.py（LLM判定・要約インタフェース）**
```python
# backend/app/ports/llm.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ClassifyResult:
    happy_score: float    # 0.0〜1.0
    category: str         # science/health/environment/animals/education/community/technology/sports/culture/mixed
    tags: list[str]
    is_ng: bool
    reason: Optional[str] = None

@dataclass
class SummaryResult:
    title_ja: str         # 整形後タイトル
    summary_3lines: str   # 日本語3行要約（\n区切り）

class ArticleClassifier(ABC):
    @abstractmethod
    async def classify(self, title: str, excerpt: str, language: str) -> ClassifyResult:
        """happy_score / category / tags / is_ng を付与する"""
        ...

class ArticleSummarizer(ABC):
    @abstractmethod
    async def summarize(self, title: str, excerpt: str, language: str) -> SummaryResult:
        """日本語3行要約を生成する"""
        ...
```

**Step 3: notifier.py（FCMインタフェース）**
```python
# backend/app/ports/notifier.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class NotificationPayload:
    title: str
    body: str
    day_key: str          # DeepLink用

class PushNotifier(ABC):
    @abstractmethod
    async def send_multicast(self, tokens: list[str], payload: NotificationPayload) -> dict:
        """FCM multicast送信。{success: int, failure: int} を返す"""
        ...
```

**Step 4: commit**
```bash
git add backend/app/ports/
git commit -m "feat: define external client interfaces (TEST-001)"
```

---

### Task 0-3: TEST-002/003 DI切替 + Stub実装【Orchestrator】

**Files:**
- Create: `backend/app/stubs/fetcher_stub.py`
- Create: `backend/app/stubs/llm_stub.py`
- Create: `backend/app/stubs/notifier_stub.py`
- Create: `backend/app/container.py`
- Create: `backend/.env.example`

**Step 1: fetcher_stub.py（固定RSS応答）**
```python
# backend/app/stubs/fetcher_stub.py
from app.ports.fetcher import ArticleFetcher, RawArticle
from datetime import datetime, timezone

STUB_ARTICLES = [
    RawArticle(
        url=f"https://example.com/article-{i}",
        title=f"Stub Article {i}: Good News",
        excerpt=f"This is a stub excerpt for article {i}. Something positive happened.",
        published_at=datetime.now(timezone.utc),
        source_id="stub-source",
        source_name="Stub News",
        thumbnail_url="https://via.placeholder.com/360x200",
        language_hint="en",
    )
    for i in range(1, 51)
]

class StubArticleFetcher(ArticleFetcher):
    async def fetch(self, feed_url: str, source_id: str, source_name: str, limit: int = 50) -> list[RawArticle]:
        return STUB_ARTICLES[:limit]
```

**Step 2: llm_stub.py（固定LLM応答）**
```python
# backend/app/stubs/llm_stub.py
from app.ports.llm import ArticleClassifier, ArticleSummarizer, ClassifyResult, SummaryResult

class StubArticleClassifier(ArticleClassifier):
    async def classify(self, title: str, excerpt: str, language: str) -> ClassifyResult:
        return ClassifyResult(
            happy_score=0.85,
            category="community",
            tags=["前向き", "進歩"],
            is_ng=False,
        )

class StubArticleSummarizer(ArticleSummarizer):
    async def summarize(self, title: str, excerpt: str, language: str) -> SummaryResult:
        return SummaryResult(
            title_ja=f"スタブ：{title[:20]}",
            summary_3lines="世界で良いことが起きました。\n多くの人が恩恵を受けています。\n今後もこの流れが続く見込みです。",
        )
```

**Step 3: notifier_stub.py**
```python
# backend/app/stubs/notifier_stub.py
from app.ports.notifier import PushNotifier, NotificationPayload

class StubPushNotifier(PushNotifier):
    async def send_multicast(self, tokens: list[str], payload: NotificationPayload) -> dict:
        print(f"[STUB] Notification: {payload.title} to {len(tokens)} tokens")
        return {"success": len(tokens), "failure": 0}
```

**Step 4: container.py（DI切替）**
```python
# backend/app/container.py
import os
from app.ports.fetcher import ArticleFetcher
from app.ports.llm import ArticleClassifier, ArticleSummarizer
from app.ports.notifier import PushNotifier

EXTERNAL_MODE = os.getenv("EXTERNAL_MODE", "stub")  # stub | real

def get_fetcher() -> ArticleFetcher:
    if EXTERNAL_MODE == "real":
        from app.clients.fetcher_real import RealArticleFetcher
        return RealArticleFetcher()
    from app.stubs.fetcher_stub import StubArticleFetcher
    return StubArticleFetcher()

def get_classifier() -> ArticleClassifier:
    if EXTERNAL_MODE == "real":
        from app.clients.llm_real import RealArticleClassifier
        return RealArticleClassifier()
    from app.stubs.llm_stub import StubArticleClassifier
    return StubArticleClassifier()

def get_summarizer() -> ArticleSummarizer:
    if EXTERNAL_MODE == "real":
        from app.clients.llm_real import RealArticleSummarizer
        return RealArticleSummarizer()
    from app.stubs.llm_stub import StubArticleSummarizer
    return StubArticleSummarizer()

def get_notifier() -> PushNotifier:
    if EXTERNAL_MODE == "real":
        from app.clients.notifier_real import RealPushNotifier
        return RealPushNotifier()
    from app.stubs.notifier_stub import StubPushNotifier
    return StubPushNotifier()
```

**Step 5: .env.example**
```
EXTERNAL_MODE=stub
GCP_PROJECT_ID=your-project-id
FIRESTORE_EMULATOR_HOST=localhost:8080
OPENAI_API_KEY=your-key
FCM_PROJECT_ID=your-project-id
```

**Step 6: commit**
```bash
git add backend/
git commit -m "feat: DI container with stub/real switching (TEST-002, TEST-003)"
```

---

## M1：API read-only + Android 一覧/詳細

### Task 1-1: BE-001〜006 GCP/Firebase 基盤【Backend Agent】

**Step 1: backend/ Python プロジェクト構造を作成**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI entry
│   ├── ports/             # インタフェース（Phase 0で作成済み）
│   ├── stubs/             # Stub実装（Phase 0で作成済み）
│   ├── clients/           # Real実装（後で追加）
│   ├── api/               # APIルーター
│   │   └── v1/
│   ├── batch/             # バッチジョブ
│   ├── notify/            # 通知ジョブ
│   ├── db/                # Firestore操作
│   └── utils/             # 共通ユーティリティ
├── tests/
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

**Step 2: requirements.txt**
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
firebase-admin==6.5.0
google-cloud-firestore==2.17.0
feedparser==6.0.11
openai==1.50.0
httpx==0.27.0
python-dotenv==1.0.1
pydantic==2.8.0
```

**Step 3: requirements-dev.txt**
```
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-mock==3.14.0
httpx==0.27.0
```

**Step 4: Dockerfile**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 5: GCP プロジェクト設定（手動 or gcloud）**
```bash
# dev プロジェクト
gcloud projects create happynews-dev --name="HappyNews Dev"
gcloud config set project happynews-dev

# Firebase 有効化
firebase projects:addfirebase happynews-dev

# 必要 API 有効化
gcloud services enable run.googleapis.com cloudscheduler.googleapis.com \
  firestore.googleapis.com secretmanager.googleapis.com fcm.googleapis.com
```

**Step 6: commit**
```bash
git add backend/
git commit -m "chore: backend project structure and GCP setup (BE-001~006)"
```

---

### Task 1-2: BE-010〜015 Firestore スキーマ【Backend Agent】

**Files:**
- Create: `backend/app/db/schema.py`
- Create: `backend/app/db/firestore_client.py`
- Create: `backend/firestore.rules`
- Create: `backend/firestore.indexes.json`

**Step 1: schema.py（全コレクション定義）**
```python
# backend/app/db/schema.py
"""
Firestore コレクション設計（inputoutput_spec.md 準拠）

コレクション:
  sources/{source_id}
  configs/global
  runs/{run_id}
  candidates/{candidate_id}
  days/{day_key}
  articles/{article_id}
  users/{uid}
  users/{uid}/bookmarks/{article_id}
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# --- sources ---
@dataclass
class Source:
    name: str
    type: str                    # rss | api | html
    feed_url: str
    homepage_url: str
    enabled: bool
    priority: int                # 1-100, 50が標準
    language_hint: str           # en | ja | unknown
    country_hint: str            # US | JP | unknown
    category_hint: str           # カテゴリセットから
    fetch_interval_minutes: int = 180
    consecutive_failures: int = 0
    quarantined: bool = False
    trust_score: int = 50
    notes: str = ""

# --- configs/global ---
@dataclass
class GlobalConfig:
    candidate_target_per_day: int = 200
    candidate_hard_limit_per_day: int = 500
    publish_count_per_day: int = 20
    fallback_max_days: int = 7
    per_category_max: dict = field(default_factory=lambda: {
        "science": 6, "health": 6, "environment": 6,
        "animals": 6, "community": 6, "mixed": 8
    })
    ng_words: list[str] = field(default_factory=list)
    ng_source_ids: list[str] = field(default_factory=list)
    ng_categories: list[str] = field(default_factory=list)
    summary_rule: dict = field(default_factory=lambda: {
        "lines": 3,
        "chars_per_line_min": 25,
        "chars_per_line_max": 40,
        "banned_phrases": ["衝撃", "炎上", "閲覧注意"]
    })
    notification_time_granularity: str = "hour"

# --- candidates ---
@dataclass
class Candidate:
    day_key: str
    source_id: str
    source_name: str
    original_url: str
    title: str
    excerpt: str
    published_at: Optional[datetime]
    collected_at: datetime
    lang: str
    rule_filtered: bool = False
    rule_filter_reasons: list[str] = field(default_factory=list)
    llm_happy_score: float = 0.0
    llm_category: str = ""
    llm_tags: list[str] = field(default_factory=list)
    llm_is_ng: bool = False
    ttl_delete_at: Optional[datetime] = None

# --- articles（掲載記事）---
@dataclass
class Article:
    id: str
    source_name: str
    source_url: str
    original_url: str
    title: str
    summary_3lines: str
    thumbnail_url: Optional[str]
    published_at: datetime
    collected_at: datetime
    tags: list[str]
    category: str
    happy_score: float
    language: str
    day_key: str

# --- days ---
@dataclass
class Day:
    day_key: str
    article_ids: list[str]
    published_at: datetime
    stats: dict  # counts, source_distribution
```

**Step 2: firestore_client.py**
```python
# backend/app/db/firestore_client.py
import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import AsyncClient

_app = None
_db: AsyncClient = None

def get_db() -> AsyncClient:
    global _app, _db
    if _db is None:
        if not firebase_admin._apps:
            if os.getenv("FIRESTORE_EMULATOR_HOST"):
                _app = firebase_admin.initialize_app()
            else:
                _app = firebase_admin.initialize_app()
        _db = firestore.AsyncClient()
    return _db
```

**Step 3: firestore.rules（セキュリティルール）**
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 公開読み取り（記事・日次）
    match /articles/{articleId} { allow read: if true; }
    match /days/{dayKey} { allow read: if true; }

    // ユーザー自身のデータのみ
    match /users/{uid} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
      match /bookmarks/{bookmarkId} {
        allow read, write: if request.auth != null && request.auth.uid == uid;
      }
    }

    // 管理データ（読み取りのみ）
    match /sources/{sourceId} { allow read: if false; }
    match /configs/{configId} { allow read: if false; }
    match /runs/{runId} { allow read: if false; }
    match /candidates/{candidateId} { allow read: if false; }
  }
}
```

**Step 4: 初期データ投入スクリプト**
```python
# backend/scripts/seed_firestore.py
"""
configs/global と sources の初期データを投入する
実行: python -m scripts.seed_firestore
"""
import asyncio
from app.db.firestore_client import get_db

INITIAL_SOURCES = [
    {"name": "Positive News", "type": "rss", "feed_url": "https://www.positive.news/feed/",
     "homepage_url": "https://www.positive.news", "enabled": True, "priority": 80,
     "language_hint": "en", "country_hint": "GB", "category_hint": "mixed",
     "consecutive_failures": 0, "quarantined": False, "trust_score": 75},
    {"name": "Good News Network", "type": "rss", "feed_url": "https://www.goodnewsnetwork.org/feed/",
     "homepage_url": "https://www.goodnewsnetwork.org", "enabled": True, "priority": 75,
     "language_hint": "en", "country_hint": "US", "category_hint": "mixed",
     "consecutive_failures": 0, "quarantined": False, "trust_score": 70},
    # ... 残り28〜58ソースは運用で追加
]

async def seed():
    db = get_db()
    # configs/global
    await db.collection("configs").document("global").set({
        "candidate_target_per_day": 200,
        "candidate_hard_limit_per_day": 500,
        "publish_count_per_day": 20,
        "fallback_max_days": 7,
        "per_category_max": {"science": 6, "health": 6, "environment": 6,
                              "animals": 6, "community": 6, "mixed": 8},
        "ng_words": ["死亡", "殺害", "爆発", "テロ"],
        "ng_source_ids": [],
        "ng_categories": [],
        "summary_rule": {"lines": 3, "chars_per_line_min": 25,
                         "chars_per_line_max": 40,
                         "banned_phrases": ["衝撃", "炎上", "閲覧注意"]},
        "notification_time_granularity": "hour",
    })
    # sources
    for s in INITIAL_SOURCES:
        await db.collection("sources").add(s)
    print("Seeded!")

if __name__ == "__main__":
    asyncio.run(seed())
```

**Step 5: commit**
```bash
git add backend/
git commit -m "feat: Firestore schema and initial data (BE-010~015)"
```

---

### Task 1-3: BE-020〜024 API サービス実装【Backend Agent】

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/utils/day_key.py`
- Create: `backend/app/api/v1/articles.py`
- Create: `backend/app/api/v1/days.py`
- Create: `backend/tests/test_api.py`

**Step 1: day_key.py（JST日付ユーティリティ）**
```python
# backend/app/utils/day_key.py
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

def today_jst() -> str:
    """JST基準の今日の day_key（YYYY-MM-DD）を返す"""
    return datetime.now(JST).strftime("%Y-%m-%d")

def parse_day_key(day_key: str) -> datetime:
    return datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=JST)
```

**Step 2: テストを書く**
```python
# backend/tests/test_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_latest_day_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/days/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "day_key" in data

@pytest.mark.asyncio
async def test_get_articles_by_day_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/days/2026-03-01/articles")
    assert resp.status_code in [200, 404]

@pytest.mark.asyncio
async def test_get_article_detail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/articles/nonexistent-id")
    assert resp.status_code == 404
```

**Step 3: テストが失敗することを確認**
```bash
cd backend
EXTERNAL_MODE=stub FIRESTORE_EMULATOR_HOST=localhost:8080 pytest tests/test_api.py -v
# Expected: ERROR (app.main が存在しない)
```

**Step 4: main.py + APIルーター実装**
```python
# backend/app/main.py
from fastapi import FastAPI
from app.api.v1 import days, articles

app = FastAPI(title="HappyNews API", version="1.0.0")
app.include_router(days.router, prefix="/v1")
app.include_router(articles.router, prefix="/v1")

@app.get("/health")
async def health(): return {"status": "ok"}
```

```python
# backend/app/api/v1/days.py
from fastapi import APIRouter, HTTPException
from app.db.firestore_client import get_db
from app.utils.day_key import today_jst
from datetime import datetime, timezone, timedelta

router = APIRouter()
JST = timezone(timedelta(hours=9))

@router.get("/days/latest")
async def get_latest():
    """最新の掲載日を返す（最大7日フォールバック）"""
    db = get_db()
    for i in range(7):
        day_key = (datetime.now(JST) - timedelta(days=i)).strftime("%Y-%m-%d")
        doc = await db.collection("days").document(day_key).get()
        if doc.exists:
            return {"day_key": day_key}
    raise HTTPException(status_code=404, detail="No published day found")

@router.get("/days/{day_key}/articles")
async def get_articles_by_day(day_key: str):
    """指定日の掲載記事一覧（happy_score desc → published_at desc）"""
    db = get_db()
    day_doc = await db.collection("days").document(day_key).get()
    if not day_doc.exists:
        # フォールバック: latest へリダイレクト相当
        latest = await get_latest()
        day_key = latest["day_key"]
        day_doc = await db.collection("days").document(day_key).get()
    if not day_doc.exists:
        raise HTTPException(status_code=404, detail="No articles found")

    data = day_doc.to_dict()
    article_ids = data.get("article_ids", [])
    articles = []
    for aid in article_ids:
        adoc = await db.collection("articles").document(aid).get()
        if adoc.exists:
            articles.append({"id": aid, **adoc.to_dict()})

    # ソート: happy_score desc → published_at desc
    articles.sort(key=lambda a: (-a.get("happy_score", 0), a.get("published_at", "")), reverse=False)
    return {"day_key": day_key, "articles": articles}
```

```python
# backend/app/api/v1/articles.py
from fastapi import APIRouter, HTTPException
from app.db.firestore_client import get_db

router = APIRouter()

@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    db = get_db()
    doc = await db.collection("articles").document(article_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"id": article_id, **doc.to_dict()}
```

**Step 5: テストを再実行（Emulator必要）**
```bash
# Firestore Emulator 起動（別ターミナル）
firebase emulators:start --only firestore

# テスト実行
EXTERNAL_MODE=stub FIRESTORE_EMULATOR_HOST=localhost:8080 pytest tests/test_api.py -v
# Expected: PASS
```

**Step 6: commit**
```bash
git add backend/
git commit -m "feat: API service with days/articles endpoints (BE-020~024)"
```

---

### Task 1-4: BE-025〜029 Bookmarks / Settings / ETag / Rate Limit【Backend Agent】

**Files:**
- Create: `backend/app/api/v1/users.py`
- Modify: `backend/app/main.py`

**Step 1: users.py（bookmarks CRUD + settings）**
```python
# backend/app/api/v1/users.py
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from app.db.firestore_client import get_db
from typing import Optional

router = APIRouter()

class SettingsUpdate(BaseModel):
    notification_enabled: Optional[bool] = None
    notification_time: Optional[int] = None   # 0-23 (HH:00)
    mute_words: Optional[list[str]] = None

@router.get("/users/me/bookmarks")
async def get_bookmarks(x_uid: str = Header(...)):
    db = get_db()
    docs = db.collection("users").document(x_uid).collection("bookmarks").stream()
    bookmarks = []
    async for doc in docs:
        bookmarks.append({"id": doc.id, **doc.to_dict()})
    # 新しい順
    bookmarks.sort(key=lambda b: b.get("saved_at", ""), reverse=True)
    return {"bookmarks": bookmarks}

@router.post("/users/me/bookmarks/{article_id}", status_code=201)
async def add_bookmark(article_id: str, x_uid: str = Header(...)):
    db = get_db()
    article = await db.collection("articles").document(article_id).get()
    if not article.exists:
        raise HTTPException(status_code=404, detail="Article not found")
    from datetime import datetime, timezone
    await db.collection("users").document(x_uid).collection("bookmarks").document(article_id).set({
        "article_id": article_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        **article.to_dict()
    })
    return {"status": "saved"}

@router.delete("/users/me/bookmarks/{article_id}", status_code=204)
async def remove_bookmark(article_id: str, x_uid: str = Header(...)):
    db = get_db()
    await db.collection("users").document(x_uid).collection("bookmarks").document(article_id).delete()

@router.put("/users/me/settings")
async def update_settings(settings: SettingsUpdate, x_uid: str = Header(...)):
    db = get_db()
    update = {k: v for k, v in settings.dict().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    await db.collection("users").document(x_uid).set(update, merge=True)
    return {"status": "updated"}
```

**Step 2: Cache-Control ヘッダー追加（BE-027）**
```python
# backend/app/api/v1/days.py に追記
from fastapi.responses import JSONResponse
from app.utils.day_key import today_jst

# get_articles_by_day の return を変更:
is_today = (day_key == today_jst())
cache_seconds = 300 if is_today else 86400  # 当日5分、過去日24h
response = JSONResponse(content={"day_key": day_key, "articles": articles})
response.headers["Cache-Control"] = f"public, max-age={cache_seconds}"
return response
```

**Step 3: commit**
```bash
git add backend/
git commit -m "feat: bookmarks/settings CRUD + cache headers (BE-025~029)"
```

---

### Task 1-5: AD-001〜005 Android 基盤【Android Agent】

**Files:**
- Create: `android/` （Android Studio プロジェクト）

**Step 1: Android プロジェクト作成**
```
android/
├── app/
│   ├── src/main/
│   │   ├── java/com/happynews/app/
│   │   │   ├── MainActivity.kt
│   │   │   ├── HappyNewsApp.kt
│   │   │   ├── di/                # Hilt モジュール
│   │   │   ├── data/
│   │   │   │   ├── api/           # Retrofit API
│   │   │   │   ├── db/            # Room DB
│   │   │   │   └── repository/    # Repository実装
│   │   │   ├── domain/
│   │   │   │   └── model/         # Article / Bookmark / UserSettings
│   │   │   └── ui/
│   │   │       ├── today/         # SC-01
│   │   │       ├── detail/        # SC-02
│   │   │       ├── bookmarks/     # SC-03
│   │   │       ├── settings/      # SC-04/05/06
│   │   │       └── theme/
│   │   └── res/
│   ├── build.gradle.kts
│   └── google-services.json       # .gitignore 対象
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

**Step 2: build.gradle.kts（app）主要依存関係**
```kotlin
dependencies {
    // Compose BOM
    implementation(platform("androidx.compose:compose-bom:2024.10.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.navigation:navigation-compose:2.8.0")

    // Hilt
    implementation("com.google.dagger:hilt-android:2.51.1")
    kapt("com.google.dagger:hilt-android-compiler:2.51.1")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")

    // Retrofit + OkHttp
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Room
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")

    // Coil（画像ロード）
    implementation("io.coil-kt:coil-compose:2.7.0")

    // Firebase
    implementation(platform("com.google.firebase:firebase-bom:33.4.0"))
    implementation("com.google.firebase:firebase-auth-ktx")
    implementation("com.google.firebase:firebase-messaging-ktx")

    // ViewModel + Lifecycle
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")

    // DataStore（設定永続化）
    implementation("androidx.datastore:datastore-preferences:1.1.1")
}
```

**Step 3: Hilt DI モジュール（AD-001）**
```kotlin
// di/NetworkModule.kt
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides @Singleton
    fun provideOkHttpClient(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .addInterceptor { chain ->
            // Firebase匿名UIDをヘッダーに付与
            val uid = FirebaseAuth.getInstance().currentUser?.uid ?: ""
            chain.proceed(chain.request().newBuilder()
                .addHeader("X-Uid", uid).build())
        }
        .build()

    @Provides @Singleton
    fun provideRetrofit(client: OkHttpClient): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    @Provides @Singleton
    fun provideHappyNewsApi(retrofit: Retrofit): HappyNewsApi =
        retrofit.create(HappyNewsApi::class.java)
}
```

**Step 4: API インタフェース（AD-002）**
```kotlin
// data/api/HappyNewsApi.kt
interface HappyNewsApi {
    @GET("v1/days/latest")
    suspend fun getLatestDay(): LatestDayResponse

    @GET("v1/days/{dayKey}/articles")
    suspend fun getArticlesByDay(@Path("dayKey") dayKey: String): ArticleListResponse

    @GET("v1/articles/{id}")
    suspend fun getArticle(@Path("id") id: String): ArticleDetailResponse

    @GET("v1/users/me/bookmarks")
    suspend fun getBookmarks(): BookmarkListResponse

    @POST("v1/users/me/bookmarks/{articleId}")
    suspend fun addBookmark(@Path("articleId") articleId: String): Response<Unit>

    @DELETE("v1/users/me/bookmarks/{articleId}")
    suspend fun removeBookmark(@Path("articleId") articleId: String): Response<Unit>

    @PUT("v1/users/me/settings")
    suspend fun updateSettings(@Body settings: SettingsRequest): Response<Unit>
}
```

**Step 5: Room DB（ローカルキャッシュ AD-003）**
```kotlin
// data/db/ArticleEntity.kt
@Entity(tableName = "articles")
data class ArticleEntity(
    @PrimaryKey val id: String,
    val title: String,
    val summary3lines: String,
    val sourceName: String,
    val publishedAt: String,
    val thumbnailUrl: String?,
    val tags: String,           // JSON配列文字列
    val category: String,
    val happyScore: Float,
    val dayKey: String,
    val originalUrl: String,
    val isBookmarked: Boolean = false,
    val cachedAt: Long = System.currentTimeMillis()
)

@Dao
interface ArticleDao {
    @Query("SELECT * FROM articles WHERE dayKey = :dayKey ORDER BY happyScore DESC, publishedAt DESC")
    fun getByDayKey(dayKey: String): Flow<List<ArticleEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(articles: List<ArticleEntity>)

    @Query("UPDATE articles SET isBookmarked = :isBookmarked WHERE id = :id")
    suspend fun updateBookmark(id: String, isBookmarked: Boolean)

    @Query("SELECT * FROM articles WHERE isBookmarked = 1 ORDER BY cachedAt DESC")
    fun getBookmarks(): Flow<List<ArticleEntity>>
}
```

**Step 6: commit**
```bash
git add android/
git commit -m "feat: Android foundation - DI/Network/Room/Coil setup (AD-001~005)"
```

---

### Task 1-6: AD-010〜011 SC-01 Today 一覧 + SC-02 詳細【Android Agent】

**Files:**
- Create: `android/app/src/main/java/com/happynews/app/ui/today/TodayScreen.kt`
- Create: `android/app/src/main/java/com/happynews/app/ui/today/TodayViewModel.kt`
- Create: `android/app/src/main/java/com/happynews/app/ui/detail/DetailScreen.kt`
- Create: `android/app/src/main/java/com/happynews/app/ui/detail/DetailViewModel.kt`

**Step 1: TodayViewModel.kt**
```kotlin
@HiltViewModel
class TodayViewModel @Inject constructor(
    private val repository: ArticleRepository
) : ViewModel() {

    sealed class UiState {
        object Loading : UiState()
        data class Success(val articles: List<Article>, val dayKey: String) : UiState()
        data class Error(val message: String, val canRetry: Boolean = true) : UiState()
        object Empty : UiState()
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init { loadArticles() }

    fun loadArticles() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            try {
                val result = repository.getTodayArticles()
                _uiState.value = if (result.isEmpty()) UiState.Empty
                                 else UiState.Success(result.articles, result.dayKey)
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "取得に失敗しました")
            }
        }
    }

    fun toggleBookmark(articleId: String) {
        viewModelScope.launch { repository.toggleBookmark(articleId) }
    }
}
```

**Step 2: TodayScreen.kt**
```kotlin
@Composable
fun TodayScreen(
    viewModel: TodayViewModel = hiltViewModel(),
    onArticleClick: (String) -> Unit,
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        is TodayViewModel.UiState.Loading -> LoadingContent()
        is TodayViewModel.UiState.Error -> ErrorContent(
            message = state.message,
            onRetry = viewModel::loadArticles
        )
        is TodayViewModel.UiState.Empty -> EmptyContent()
        is TodayViewModel.UiState.Success -> {
            val pullRefreshState = rememberPullToRefreshState()
            PullToRefreshBox(state = pullRefreshState, onRefresh = viewModel::loadArticles) {
                LazyColumn {
                    items(state.articles, key = { it.id }) { article ->
                        ArticleCard(
                            article = article,
                            onClick = { onArticleClick(article.id) },
                            onBookmarkToggle = { viewModel.toggleBookmark(article.id) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ArticleCard(article: Article, onClick: () -> Unit, onBookmarkToggle: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().padding(8.dp).clickable(onClick = onClick)) {
        Row {
            // サムネ（遅延ロード + プレースホルダー）
            AsyncImage(
                model = ImageRequest.Builder(LocalContext.current)
                    .data(article.thumbnailUrl)
                    .crossfade(true)
                    .build(),
                contentDescription = null,
                modifier = Modifier.size(80.dp),
                error = painterResource(R.drawable.placeholder),
            )
            Column(modifier = Modifier.weight(1f).padding(8.dp)) {
                Text(article.title, style = MaterialTheme.typography.titleSmall, maxLines = 2)
                Text(article.summary3lines, style = MaterialTheme.typography.bodySmall, maxLines = 3)
                Row {
                    Text(article.sourceName, style = MaterialTheme.typography.labelSmall)
                    Spacer(Modifier.weight(1f))
                    IconButton(onClick = onBookmarkToggle) {
                        Icon(
                            imageVector = if (article.isBookmarked) Icons.Filled.Bookmark else Icons.Outlined.BookmarkBorder,
                            contentDescription = "保存"
                        )
                    }
                }
            }
        }
    }
}
```

**Step 3: DetailScreen.kt + DetailViewModel.kt**
```kotlin
@HiltViewModel
class DetailViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val repository: ArticleRepository
) : ViewModel() {
    private val articleId: String = checkNotNull(savedStateHandle["articleId"])

    sealed class UiState {
        object Loading : UiState()
        data class Success(val article: Article) : UiState()
        data class Error(val message: String) : UiState()
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            try {
                val article = repository.getArticle(articleId)
                _uiState.value = UiState.Success(article)
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "取得に失敗しました")
            }
        }
    }

    fun toggleBookmark() {
        val s = _uiState.value as? UiState.Success ?: return
        viewModelScope.launch { repository.toggleBookmark(s.article.id) }
    }
}

@Composable
fun DetailScreen(viewModel: DetailViewModel = hiltViewModel(), onBack: () -> Unit) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current

    Scaffold(topBar = { TopAppBar(title = {}, navigationIcon = {
        IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "戻る") }
    })}) { padding ->
        when (val state = uiState) {
            is DetailViewModel.UiState.Loading -> LoadingContent()
            is DetailViewModel.UiState.Error -> ErrorContent(state.message)
            is DetailViewModel.UiState.Success -> {
                val article = state.article
                Column(modifier = Modifier.padding(padding).verticalScroll(rememberScrollState())) {
                    Text(article.title, style = MaterialTheme.typography.headlineSmall)
                    Text(article.summary3lines, style = MaterialTheme.typography.bodyMedium)
                    Text("出典: ${article.sourceName}", style = MaterialTheme.typography.labelMedium)
                    Row {
                        // 保存
                        IconButton(onClick = viewModel::toggleBookmark) {
                            Icon(if (article.isBookmarked) Icons.Filled.Bookmark else Icons.Outlined.BookmarkBorder, "保存")
                        }
                        // 共有
                        IconButton(onClick = {
                            val intent = Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_TEXT, "${article.title}\n${article.originalUrl}\n#ハッピーニュース")
                            }
                            context.startActivity(Intent.createChooser(intent, "共有"))
                        }) { Icon(Icons.Default.Share, "共有") }
                        // 出典
                        IconButton(onClick = {
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(article.originalUrl)))
                        }) { Icon(Icons.Default.OpenInBrowser, "出典を開く") }
                    }
                }
            }
        }
    }
}
```

**Step 4: commit**
```bash
git add android/
git commit -m "feat: SC-01 Today list + SC-02 Detail screen (AD-010, AD-011)"
```

---

## M2：ブックマーク + 設定 + キャッシュ

### Task 2-1: AD-012〜015 SC-03〜SC-06 残4画面【Android Agent】

**Files:**
- Create: `android/.../ui/bookmarks/BookmarksScreen.kt`
- Create: `android/.../ui/settings/SettingsScreen.kt`
- Create: `android/.../ui/settings/NotificationSettingsScreen.kt`
- Create: `android/.../ui/settings/LegalScreen.kt`

**Step 1: BookmarksScreen.kt（SC-03）**
```kotlin
@Composable
fun BookmarksScreen(viewModel: BookmarksViewModel = hiltViewModel(), onArticleClick: (String) -> Unit) {
    val bookmarks by viewModel.bookmarks.collectAsStateWithLifecycle()
    if (bookmarks.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(Icons.Outlined.BookmarkBorder, null, modifier = Modifier.size(64.dp))
                Text("保存した記事がありません")
                Text("記事を読んで♡マークをタップしてみましょう", style = MaterialTheme.typography.bodySmall)
            }
        }
    } else {
        LazyColumn {
            items(bookmarks, key = { it.id }) { article ->
                ArticleCard(article = article, onClick = { onArticleClick(article.id) },
                    onBookmarkToggle = { viewModel.removeBookmark(article.id) })
            }
        }
    }
}
```

**Step 2: SettingsScreen.kt（SC-04）**
```kotlin
@Composable
fun SettingsScreen(
    onNotificationClick: () -> Unit,
    onLegalClick: () -> Unit,
    viewModel: SettingsViewModel = hiltViewModel()
) {
    val muteWords by viewModel.muteWords.collectAsStateWithLifecycle()
    var newWord by remember { mutableStateOf("") }

    Column {
        ListItem(headlineContent = { Text("通知設定") },
                 modifier = Modifier.clickable(onClick = onNotificationClick))
        HorizontalDivider()
        // ミュートワード
        Text("ミュートワード", style = MaterialTheme.typography.titleSmall)
        muteWords.forEach { word ->
            ListItem(
                headlineContent = { Text(word) },
                trailingContent = {
                    IconButton(onClick = { viewModel.removeMuteWord(word) }) {
                        Icon(Icons.Default.Close, "削除")
                    }
                }
            )
        }
        OutlinedTextField(
            value = newWord, onValueChange = { newWord = it },
            label = { Text("ミュートワードを追加") },
            trailingIcon = {
                IconButton(onClick = { viewModel.addMuteWord(newWord); newWord = "" }) {
                    Icon(Icons.Default.Add, "追加")
                }
            }
        )
        HorizontalDivider()
        ListItem(headlineContent = { Text("法務/情報") },
                 modifier = Modifier.clickable(onClick = onLegalClick))
    }
}
```

**Step 3: NotificationSettingsScreen.kt（SC-05）**
```kotlin
@Composable
fun NotificationSettingsScreen(viewModel: NotificationViewModel = hiltViewModel()) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val hasPermission by viewModel.hasNotificationPermission.collectAsStateWithLifecycle()

    Column {
        // OS権限チェック
        if (!hasPermission) {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                Text("通知が許可されていません")
                Button(onClick = {
                    context.startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).apply {
                        putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
                    })
                }) { Text("通知設定を開く") }
            }
        }
        // 通知ON/OFF
        ListItem(
            headlineContent = { Text("通知を受け取る") },
            trailingContent = {
                Switch(checked = settings.enabled,
                       onCheckedChange = { viewModel.toggleNotification(it) })
            }
        )
        // 時刻選択（HH:00）
        if (settings.enabled) {
            Text("通知時刻")
            (6..22).forEach { hour ->
                ListItem(
                    headlineContent = { Text(String.format("%02d:00", hour)) },
                    leadingContent = {
                        RadioButton(selected = settings.hour == hour,
                                    onClick = { viewModel.setNotificationHour(hour) })
                    }
                )
            }
        }
    }
}
```

**Step 4: LegalScreen.kt（SC-06）**
```kotlin
@Composable
fun LegalScreen() {
    val context = LocalContext.current
    Column {
        ListItem(headlineContent = { Text("出典方針") },
                 supportingContent = { Text("要約+リンク中心、本文保存なし、出典明記") })
        HorizontalDivider()
        ListItem(headlineContent = { Text("利用規約") },
                 modifier = Modifier.clickable {
                     context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://YOUR_DOMAIN/terms")))
                 })
        ListItem(headlineContent = { Text("プライバシーポリシー") },
                 modifier = Modifier.clickable {
                     context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://YOUR_DOMAIN/privacy")))
                 })
        ListItem(headlineContent = { Text("お問い合わせ") },
                 modifier = Modifier.clickable {
                     context.startActivity(Intent(Intent.ACTION_SENDTO, Uri.parse("mailto:support@YOUR_DOMAIN")))
                 })
    }
}
```

**Step 5: commit**
```bash
git add android/
git commit -m "feat: SC-03 Bookmarks + SC-04~06 Settings screens (AD-012~015)"
```

---

## M3：日次バッチ 20本/日

### Task 3-1: BE-030〜043 Daily Batch 全ステップ【Backend Agent】

**Files:**
- Create: `backend/app/batch/daily_batch.py`
- Create: `backend/app/batch/steps/collect.py`
- Create: `backend/app/batch/steps/normalize.py`
- Create: `backend/app/batch/steps/rule_filter.py`
- Create: `backend/app/batch/steps/classify.py`
- Create: `backend/app/batch/steps/rank.py`
- Create: `backend/app/batch/steps/summarize.py`
- Create: `backend/app/batch/steps/publish.py`
- Create: `backend/app/clients/fetcher_real.py`
- Create: `backend/app/clients/llm_real.py`
- Create: `backend/tests/test_batch.py`

**Step 1: テストを書く（外部ゼロ・Stub使用）**
```python
# backend/tests/test_batch.py
import pytest
import os
os.environ["EXTERNAL_MODE"] = "stub"
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

from app.batch.daily_batch import run_daily_batch

@pytest.mark.asyncio
async def test_batch_publishes_20_articles():
    """バッチが20本の記事を掲載することを確認"""
    result = await run_daily_batch(day_key="2026-03-01", dry_run=False, mode="dev")
    assert result["published"] == 20
    assert result["status"] == "succeeded"

@pytest.mark.asyncio
async def test_batch_is_idempotent():
    """同一day_keyで再実行しても冪等であることを確認"""
    result1 = await run_daily_batch(day_key="2026-03-02", dry_run=False, mode="dev")
    result2 = await run_daily_batch(day_key="2026-03-02", dry_run=False, mode="dev")
    assert result1["published"] == result2["published"]

@pytest.mark.asyncio
async def test_batch_respects_category_limits():
    """カテゴリ上限が守られることを確認"""
    result = await run_daily_batch(day_key="2026-03-03", dry_run=True, mode="dev")
    # カテゴリ分布チェック
    assert all(v <= 8 for v in result.get("category_counts", {}).values())
```

**Step 2: collect.py（BE-033〜035）**
```python
# backend/app/batch/steps/collect.py
import hashlib
from app.db.firestore_client import get_db
from app.container import get_fetcher

async def collect_candidates(day_key: str, target: int, hard_limit: int) -> list[dict]:
    db = get_db()
    fetcher = get_fetcher()

    # enabled sources を priority 降順で取得
    sources = []
    async for doc in db.collection("sources").where("enabled", "==", True).stream():
        sources.append({"id": doc.id, **doc.to_dict()})
    sources.sort(key=lambda s: -s.get("priority", 50))

    candidates = []
    seen_urls = set()

    for source in sources:
        if len(candidates) >= hard_limit:
            break
        if len(candidates) >= target and len(sources) > 0:
            break  # 目標達成したら停止

        articles = await fetcher.fetch(
            feed_url=source["feed_url"],
            source_id=source["id"],
            source_name=source["name"],
            limit=50
        )

        for article in articles:
            # URL正規化・重複排除
            url_hash = hashlib.sha256(article.url.encode()).hexdigest()[:16]
            if url_hash in seen_urls:
                continue
            seen_urls.add(url_hash)

            candidates.append({
                "candidate_id": f"{source['id']}_{url_hash}",
                "day_key": day_key,
                "source_id": source["id"],
                "source_name": source["name"],
                "original_url": article.url,
                "title": article.title,
                "excerpt": article.excerpt[:500],   # 全文保存しない
                "published_at": article.published_at,
                "lang": article.language_hint,
                "thumbnail_url": article.thumbnail_url,
                "rule_filtered": False,
                "rule_filter_reasons": [],
            })

    return candidates[:hard_limit]
```

**Step 3: rule_filter.py（BE-036）**
```python
# backend/app/batch/steps/rule_filter.py
async def apply_rule_filter(candidates: list[dict], config: dict) -> list[dict]:
    ng_words = config.get("ng_words", [])
    ng_source_ids = config.get("ng_source_ids", [])
    ng_categories = config.get("ng_categories", [])

    for c in candidates:
        reasons = []
        # NGソース
        if c["source_id"] in ng_source_ids:
            reasons.append(f"ng_source: {c['source_id']}")
        # NGワード（タイトル + excerpt）
        text = (c["title"] + " " + c["excerpt"]).lower()
        for w in ng_words:
            if w.lower() in text:
                reasons.append(f"ng_word: {w}")
        if reasons:
            c["rule_filtered"] = True
            c["rule_filter_reasons"] = reasons

    return candidates
```

**Step 4: classify.py（BE-037）**
```python
# backend/app/batch/steps/classify.py
from app.container import get_classifier

async def classify_candidates(candidates: list[dict]) -> list[dict]:
    classifier = get_classifier()
    # rule_filteredでないものだけ分類
    unfiltered = [c for c in candidates if not c["rule_filtered"]]

    for c in unfiltered:
        result = await classifier.classify(
            title=c["title"],
            excerpt=c["excerpt"],
            language=c["lang"]
        )
        c["llm"] = {
            "happy_score": result.happy_score,
            "category": result.category,
            "tags": result.tags,
            "is_ng": result.is_ng,
        }

    return candidates
```

**Step 5: rank.py（BE-038）**
```python
# backend/app/batch/steps/rank.py
async def rank_and_select(candidates: list[dict], publish_count: int, per_category_max: dict) -> list[dict]:
    eligible = [c for c in candidates
                if not c["rule_filtered"] and not c.get("llm", {}).get("is_ng", True)]
    eligible.sort(key=lambda c: -c.get("llm", {}).get("happy_score", 0))

    selected = []
    category_counts = {}

    def try_select(items, cat_max):
        for c in items:
            if len(selected) >= publish_count:
                break
            category = c.get("llm", {}).get("category", "mixed")
            max_for_cat = cat_max.get(category, cat_max.get("mixed", 8))
            if category_counts.get(category, 0) >= max_for_cat:
                continue
            selected.append(c)
            category_counts[category] = category_counts.get(category, 0) + 1

    # 通常選出
    try_select(eligible, per_category_max)

    # 足りない場合: カテゴリ上限を緩める（+1）
    if len(selected) < publish_count:
        relaxed = {k: v + 1 for k, v in per_category_max.items()}
        try_select(eligible, relaxed)

    return selected
```

**Step 6: summarize.py（BE-039）**
```python
# backend/app/batch/steps/summarize.py
from app.container import get_summarizer

async def summarize_selected(selected: list[dict]) -> list[dict]:
    summarizer = get_summarizer()
    for c in selected:
        result = await summarizer.summarize(
            title=c["title"],
            excerpt=c["excerpt"],
            language=c["lang"]
        )
        c["summary"] = {
            "title_ja": result.title_ja,
            "summary_3lines": result.summary_3lines,
        }
    return selected
```

**Step 7: publish.py（BE-040〜042 原子的確定）**
```python
# backend/app/batch/steps/publish.py
from datetime import datetime, timezone
from app.db.firestore_client import get_db
import uuid

async def publish(day_key: str, selected: list[dict], run_id: str, dry_run: bool = False) -> dict:
    if dry_run:
        return {"published": len(selected), "dry_run": True}

    db = get_db()
    article_ids = []

    # articles を一括保存
    batch = db.batch()
    for c in selected:
        article_id = str(uuid.uuid4())
        article_ids.append(article_id)
        ref = db.collection("articles").document(article_id)
        batch.set(ref, {
            "id": article_id,
            "source_name": c["source_name"],
            "source_url": "",
            "original_url": c["original_url"],
            "title": c["summary"]["title_ja"],
            "summary_3lines": c["summary"]["summary_3lines"],
            "thumbnail_url": c.get("thumbnail_url"),
            "published_at": c.get("published_at", datetime.now(timezone.utc)).isoformat(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "tags": c.get("llm", {}).get("tags", []),
            "category": c.get("llm", {}).get("category", "mixed"),
            "happy_score": c.get("llm", {}).get("happy_score", 0.0),
            "language": c.get("lang", "unknown"),
            "day_key": day_key,
        })

    # days/{day_key} を確定
    day_ref = db.collection("days").document(day_key)
    batch.set(day_ref, {
        "day_key": day_key,
        "article_ids": article_ids,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "stats": {"count": len(article_ids)},
    })

    await batch.commit()
    return {"published": len(article_ids)}
```

**Step 8: daily_batch.py（オーケストレーター）**
```python
# backend/app/batch/daily_batch.py
from datetime import datetime, timezone
from app.db.firestore_client import get_db
from app.utils.day_key import today_jst
from app.batch.steps.collect import collect_candidates
from app.batch.steps.rule_filter import apply_rule_filter
from app.batch.steps.classify import classify_candidates
from app.batch.steps.rank import rank_and_select
from app.batch.steps.summarize import summarize_selected
from app.batch.steps.publish import publish
import uuid

async def run_daily_batch(day_key: str = None, dry_run: bool = False, mode: str = "prod") -> dict:
    if day_key is None:
        day_key = today_jst()

    run_id = f"run_{day_key}_{str(uuid.uuid4())[:8]}"
    db = get_db()

    # runs/{run_id} を running で開始
    run_ref = db.collection("runs").document(run_id)
    await run_ref.set({"day_key": day_key, "status": "running",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "mode": mode})
    counts = {}
    try:
        # configs/global 読み込み
        config_doc = await db.collection("configs").document("global").get()
        config = config_doc.to_dict() if config_doc.exists else {}
        target = config.get("candidate_target_per_day", 200)
        hard_limit = config.get("candidate_hard_limit_per_day", 500)
        publish_count = config.get("publish_count_per_day", 20)
        per_category_max = config.get("per_category_max", {"mixed": 8})

        # Step 1: Collect
        candidates = await collect_candidates(day_key, target, hard_limit)
        counts["fetched"] = len(candidates)

        # Step 2: Rule Filter
        candidates = await apply_rule_filter(candidates, config)
        counts["rule_filtered"] = sum(1 for c in candidates if c["rule_filtered"])

        # Step 3: Classify
        candidates = await classify_candidates(candidates)
        counts["llm_scored"] = sum(1 for c in candidates if "llm" in c)

        # Step 4: Rank & Select
        selected = await rank_and_select(candidates, publish_count, per_category_max)
        counts["selected"] = len(selected)

        # Step 5: Summarize
        selected = await summarize_selected(selected)
        counts["summarized"] = len(selected)

        # Step 6: Publish
        result = await publish(day_key, selected, run_id, dry_run)
        counts["published"] = result["published"]

        # runs を succeeded で完了
        await run_ref.update({"status": "succeeded",
                               "finished_at": datetime.now(timezone.utc).isoformat(),
                               "counts": counts})
        return {"status": "succeeded", **counts}

    except Exception as e:
        await run_ref.update({"status": "failed",
                               "finished_at": datetime.now(timezone.utc).isoformat(),
                               "errors": [str(e)], "counts": counts})
        raise
```

**Step 9: Real クライアント実装（BE-033〜037 実弾）**
```python
# backend/app/clients/fetcher_real.py
import feedparser
import httpx
from app.ports.fetcher import ArticleFetcher, RawArticle
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

class RealArticleFetcher(ArticleFetcher):
    async def fetch(self, feed_url: str, source_id: str, source_name: str, limit: int = 50) -> list[RawArticle]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(feed_url, follow_redirects=True)
            resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        articles = []
        for entry in feed.entries[:limit]:
            try:
                published = parsedate_to_datetime(entry.get("published", ""))
            except Exception:
                published = datetime.now(timezone.utc)
            thumbnail = None
            if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                thumbnail = entry.media_thumbnail[0].get("url")
            articles.append(RawArticle(
                url=entry.get("link", ""),
                title=entry.get("title", ""),
                excerpt=(entry.get("summary", "") or entry.get("description", ""))[:500],
                published_at=published,
                source_id=source_id,
                source_name=source_name,
                thumbnail_url=thumbnail,
            ))
        return articles
```

```python
# backend/app/clients/llm_real.py
from openai import AsyncOpenAI
from app.ports.llm import ArticleClassifier, ArticleSummarizer, ClassifyResult, SummaryResult
import json

CATEGORIES = ["science","health","environment","animals","education","community","technology","sports","culture","mixed"]

class RealArticleClassifier(ArticleClassifier):
    def __init__(self):
        self.client = AsyncOpenAI()

    async def classify(self, title: str, excerpt: str, language: str) -> ClassifyResult:
        prompt = f"""以下のニュース記事を分析してJSON形式で回答してください。
タイトル: {title}
抜粋: {excerpt[:300]}

回答形式:
{{"happy_score": 0.0-1.0, "category": "{'/'.join(CATEGORIES)}", "tags": ["タグ1","タグ2"], "is_ng": false/true}}

is_ng=trueの条件: 事件・暴力・戦争・災害・炎上・ヘイト・過度な悲惨"""
        resp = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=200,
        )
        data = json.loads(resp.choices[0].message.content)
        return ClassifyResult(
            happy_score=float(data.get("happy_score", 0)),
            category=data.get("category", "mixed"),
            tags=data.get("tags", []),
            is_ng=bool(data.get("is_ng", False)),
        )

class RealArticleSummarizer(ArticleSummarizer):
    def __init__(self):
        self.client = AsyncOpenAI()

    async def summarize(self, title: str, excerpt: str, language: str) -> SummaryResult:
        prompt = f"""以下のニュース記事を日本語3行で要約してください。
元記事: {title} / {excerpt[:500]}

ルール:
- 必ず3行（改行2つ）
- 各行25〜40文字
- 構成: 1行目=何が起きたか(結論) / 2行目=具体(誰が/どこで) / 3行目=前向きな意味
- 禁止: 衝撃/炎上/閲覧注意/悲惨さの強調/根拠のない断定

整形後タイトル（30文字以内）と要約3行をJSONで返してください:
{{"title_ja": "...", "summary_3lines": "1行目\\n2行目\\n3行目"}}"""
        resp = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=300,
        )
        data = json.loads(resp.choices[0].message.content)
        return SummaryResult(
            title_ja=data.get("title_ja", title[:30]),
            summary_3lines=data.get("summary_3lines", ""),
        )
```

**Step 10: Cloud Scheduler（BE-031）**
```bash
# 日次バッチ: JST 03:00
gcloud scheduler jobs create http happynews-daily-batch \
  --schedule="0 3 * * *" \
  --time-zone="Asia/Tokyo" \
  --uri="https://batch-job-url/run" \
  --http-method=POST \
  --message-body='{"day_key": null}'
```

**Step 11: テスト実行**
```bash
EXTERNAL_MODE=stub FIRESTORE_EMULATOR_HOST=localhost:8080 pytest tests/test_batch.py -v
# Expected: PASS (3 tests)
```

**Step 12: commit**
```bash
git add backend/
git commit -m "feat: daily batch pipeline collect→filter→LLM→rank→summarize→publish (BE-030~043)"
```

---

## M4：通知 + DeepLink

### Task 4-1: BE-050〜055 FCM 通知ジョブ【Backend Agent】

**Files:**
- Create: `backend/app/notify/notify_job.py`
- Create: `backend/app/clients/notifier_real.py`

**Step 1: notifier_real.py（FCM送信）**
```python
# backend/app/clients/notifier_real.py
import firebase_admin.messaging as fcm_messaging
from app.ports.notifier import PushNotifier, NotificationPayload

class RealPushNotifier(PushNotifier):
    async def send_multicast(self, tokens: list[str], payload: NotificationPayload) -> dict:
        message = fcm_messaging.MulticastMessage(
            tokens=tokens,
            notification=fcm_messaging.Notification(
                title=payload.title,
                body=payload.body,
            ),
            data={"day_key": payload.day_key, "screen": "today"},
            android=fcm_messaging.AndroidConfig(
                notification=fcm_messaging.AndroidNotification(
                    channel_id="happynews_daily",
                )
            )
        )
        response = fcm_messaging.send_each_for_multicast(message)
        return {"success": response.success_count, "failure": response.failure_count}
```

**Step 2: notify_job.py（毎時実行 HH:00）**
```python
# backend/app/notify/notify_job.py
from datetime import datetime, timezone, timedelta
from app.db.firestore_client import get_db
from app.container import get_notifier
from app.ports.notifier import NotificationPayload
from app.utils.day_key import today_jst

BATCH_SIZE = 500  # FCM上限

async def run_notify_job(hour_slot: int = None) -> dict:
    if hour_slot is None:
        hour_slot = datetime.now(timezone(timedelta(hours=9))).hour

    db = get_db()
    notifier = get_notifier()
    day_key = today_jst()

    # 対象ユーザー: notification_enabled=True & notification_time==hour_slot
    users = []
    async for doc in db.collection("users") \
        .where("notification_enabled", "==", True) \
        .where("notification_time", "==", hour_slot).stream():
        users.append(doc.to_dict())

    tokens = [u.get("fcm_token") for u in users if u.get("fcm_token")]
    if not tokens:
        return {"sent": 0, "no_tokens": True}

    payload = NotificationPayload(
        title="今日のハッピーニュース",
        body="世界の良い出来事を20本まとめました",
        day_key=day_key,
    )

    total_success = 0
    for i in range(0, len(tokens), BATCH_SIZE):
        batch_tokens = tokens[i:i+BATCH_SIZE]
        result = await notifier.send_multicast(batch_tokens, payload)
        total_success += result["success"]

    return {"sent": total_success, "total_targets": len(tokens)}
```

**Step 3: Cloud Scheduler（BE-051：毎時）**
```bash
gcloud scheduler jobs create http happynews-hourly-notify \
  --schedule="0 * * * *" \
  --time-zone="Asia/Tokyo" \
  --uri="https://notify-job-url/run" \
  --http-method=POST
```

**Step 4: commit**
```bash
git add backend/
git commit -m "feat: FCM notification job hourly (BE-050~055)"
```

---

### Task 4-2: AD-005 Android DeepLink + 通知受信【Android Agent】

**Files:**
- Modify: `android/app/src/main/AndroidManifest.xml`
- Create: `android/.../HappyNewsMessagingService.kt`

**Step 1: AndroidManifest.xml にDeepLink設定**
```xml
<activity android:name=".MainActivity">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="happynews" android:host="today" />
    </intent-filter>
</activity>
```

**Step 2: FCM受信サービス**
```kotlin
class HappyNewsMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        // トークンをバックエンドに登録
        CoroutineScope(Dispatchers.IO).launch {
            settingsRepository.updateFcmToken(token)
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val dayKey = message.data["day_key"] ?: return
        val intent = Intent(this, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            data = Uri.parse("happynews://today?day_key=$dayKey")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val notification = NotificationCompat.Builder(this, "happynews_daily")
            .setContentTitle(message.notification?.title ?: "今日のハッピーニュース")
            .setContentText(message.notification?.body)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(PendingIntent.getActivity(this, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE))
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(this).notify(1, notification)
    }
}
```

**Step 3: commit**
```bash
git add android/
git commit -m "feat: DeepLink + FCM notification receiver (AD-005)"
```

---

## M5：監視/アラート + リリース準備

### Task 5-1: BE-060〜062 Cloud Monitoring 設定【Backend Agent】

**Step 1: 構造化ログ（BE-062）**
```python
# backend/app/utils/logger.py
import logging
import json
from datetime import datetime, timezone

class StructuredLogger:
    def __init__(self, name: str):
        self.name = name

    def log(self, severity: str, message: str, **kwargs):
        entry = {"severity": severity, "message": message,
                 "timestamp": datetime.now(timezone.utc).isoformat(),
                 "logger": self.name, **kwargs}
        print(json.dumps(entry, ensure_ascii=False))

    def info(self, msg, **kw): self.log("INFO", msg, **kw)
    def warning(self, msg, **kw): self.log("WARNING", msg, **kw)
    def error(self, msg, **kw): self.log("ERROR", msg, **kw)
```

**Step 2: アラートポリシー（BE-061）**
```bash
# バッチ失敗アラート
gcloud monitoring alert-policies create \
  --policy-from-file=monitoring/batch_failure_alert.yaml

# API 5xx アラート
gcloud monitoring alert-policies create \
  --policy-from-file=monitoring/api_5xx_alert.yaml
```

**Step 3: commit**
```bash
git add backend/
git commit -m "feat: structured logging + monitoring alerts (BE-060~062)"
```

---

### Task 5-2: OP-001〜005 リリース準備【Orchestrator】

**Files:**
- Create: `docs/store/store_listing.md`
- Create: `docs/ops/daily_ops.md`
- Create: `docs/ops/rollback_procedure.md`

**Step 1: store_listing.md**
```markdown
# Google Play ストア掲載情報

## アプリ名
ハッピーニュース - 毎日の前向きなニュース

## 短い説明（80文字以内）
世界の良いニュースだけを毎日20本。1分で気分を前向きに。

## 詳細説明（4000文字以内）
ネガティブなニュースに疲れていませんか？
「ハッピーニュース」は、世界中の前向きな出来事だけを厳選してお届けするアプリです。
...（残りは運用時に作成）
```

**Step 2: commit**
```bash
git add docs/
git commit -m "docs: store listing and ops procedures (OP-001~005)"
```

---

## M6：CI 完全化

### Task 6-1: TEST-050〜052 GitHub Actions CI【Orchestrator】

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/nightly.yml`

**Step 1: ci.yml（毎PR・外部ゼロ）**
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - name: Install deps
        run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - name: Start Firestore Emulator
        run: |
          npm install -g firebase-tools
          firebase emulators:start --only firestore &
          sleep 5
      - name: Run tests
        env:
          EXTERNAL_MODE: stub
          FIRESTORE_EMULATOR_HOST: localhost:8080
        run: cd backend && pytest tests/ -v

  android-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: {java-version: '17', distribution: temurin}
      - name: Setup Android SDK
        uses: android-actions/setup-android@v3
      - name: Build
        run: cd android && ./gradlew assembleDebug lintDebug
      - name: Unit tests
        run: cd android && ./gradlew testDebugUnitTest
```

**Step 2: nightly.yml（実弾スモーク・上限固定）**
```yaml
name: Nightly Smoke
on:
  schedule:
    - cron: '0 20 * * *'   # JST 05:00
  workflow_dispatch:

jobs:
  llm-smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - name: LLM smoke (20 articles, real)
        env:
          EXTERNAL_MODE: real
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: cd backend && pytest tests/nightly/ -v -k "smoke" --limit=20
```

**Step 3: commit & push**
```bash
git add .github/
git commit -m "feat: GitHub Actions CI + Nightly smoke (TEST-050~052)"
git push
```

---

## Progress.md 更新フォーマット（各マイルストーン完了時）

各エージェントはマイルストーン完了時に `docs/progress.md` を以下のフォーマットで更新し、GitHub に push すること。

```markdown
## 0. 今回の報告サマリ
- 完了: [マイルストーン名]（タスクID一覧）
- 未完了: [残タスク]
- ブロッカー: [あれば記載]

## 1. 完了タスク ✅
- TASK-ID: 概要

## 2. 進行中タスク 🟡
- TASK-ID: 現状/残作業

## 3. 次にやること
- TASK-ID: 優先順

## 4. Token 80% 対応（該当する場合）
- 中断箇所:
- 再開手順:
```

---

## Token 80% 超過時の緊急停止手順

1. 現在作業中のタスクを「きりの良い単位」で完了させる（ファイル単位 or テスト PASS まで）
2. `docs/progress.md` を更新（上記フォーマット）
3. `git add . && git commit -m "wip: [現在地] Token limit pause" && git push`
4. 作業停止

次セッション開始時: `docs/progress.md` を読んで「次にやること」から再開する。
