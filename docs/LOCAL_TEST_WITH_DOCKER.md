# ローカル検査環境 手順書（Docker）
対象：HappyNews / backend + Firestore Emulator  
目的：**誰がやっても同じ手順で**「API・日次バッチ・データ投入・テスト」を実行できるようにする  
前提：Windows/macOS/Linux いずれも可（WindowsはDocker Desktop + WSL2推奨）

---

## 0. この手順でできること
- Firestore Emulator を起動する
- backend API（FastAPI）を起動する
- `configs/global` と `sources` を投入する（seed）
- 日次バッチを手動実行して `days/{day_key}` に20本生成する
- APIを叩いて結果を確認する
- backendのテスト（外部ゼロ）を回す

---

## 1. 前提ツール
- Docker / Docker Compose が使えること

確認コマンド：
```bash
docker version
docker compose version
docker run --rm hello-world
````

---

## 2. 起動（API + Firestore Emulator）

> 以降のコマンドは **リポジトリの `backend/` ディレクトリ**で実行する

```bash
cd backend
docker compose up --build -d
```

### 起動確認

* API：`http://localhost:8080`
* Firestore Emulator：`http://localhost:8081`

  * ※composeでホスト `8081` → コンテナ `8080` へ割当（ポート衝突回避）

ヘルスチェック（ある場合）：

```bash
curl http://localhost:8080/health
```

---

## 3. 初期データ投入（seed）

> 注意：`backend/Dockerfile` は `app/` のみコピーする構成のため、`scripts/` を使う場合は **実行時に /app へマウント**して動かす

### 3.1 `configs/global` と `sources` を投入

```bash
docker compose run --rm -v "$(pwd)":/app api python -m scripts.seed_firestore
```

### 3.2 投入確認（任意）

Firestore Emulator UI（`http://localhost:8081`）で以下を確認：

* `configs/global`
* `sources/*`

---

## 4. 日次バッチを手動実行（外部ゼロ：stub）

```bash
docker compose run --rm -v "$(pwd)":/app api python -m app.batch.job
```

### 合格条件（必須）

Firestore Emulator UI（`http://localhost:8081`）で：

* `days/{day_key}` が作成されている
* `days/{day_key}.article_ids` が **20件**
* `articles` が20件作成されている

---

## 5. APIで結果確認

### 5.1 最新日を取得

```bash
curl http://localhost:8080/v1/days/latest
```

### 5.2 記事一覧を取得

`latest` の返り値に含まれる `day_key` を使って：

```bash
curl http://localhost:8080/v1/days/<day_key>/articles
```

### 合格条件（推奨）

* 20本返る
* 並び順：`happy_score desc` → `published_at desc`
* 当日0件時でも latest へフォールバックする

---

## 6. backendテスト実行（外部ゼロ）

> テスト依存は `requirements-dev.txt` にあるため、実行時にだけインストールして回す

```bash
docker compose run --rm -v "$(pwd)":/app api bash -lc \
  "pip install -r requirements-dev.txt && pytest -q --ignore=tests/nightly"
```

### 合格条件

* すべてPASS（nightlyは除外）

---

## 7. 終了

```bash
docker compose down
```

---

## 8. よくある詰まりポイント

### 8.1 ポートが使用中で起動できない

* 8080（API）/ 8081（Emulator）が埋まっている可能性
* 対処：`backend/docker-compose.yml` の `ports:` を変更する

### 8.2 Windowsで `$(pwd)` が動かない

PowerShellの場合は `$(pwd)` がオブジェクトになるので、以下を使用：

```powershell
docker compose run --rm -v ${PWD}:/app api python -m scripts.seed_firestore
docker compose run --rm -v ${PWD}:/app api python -m app.batch.job
docker compose run --rm -v ${PWD}:/app api bash -lc "pip install -r requirements-dev.txt && pytest -q --ignore=tests/nightly"
```

### 8.3 Firestore Emulator 接続先が分からない

* コンテナ内から：`firestore:8080`
* ホストPCから：`localhost:8081`

本手順は「seed/batch/test」を **コンテナ内で実行**するので、接続ズレが起きにくい。

---

## 9. Staging/Prod（参考）

ローカルは `EXTERNAL_MODE=stub` 前提。
本番相当（ニュース取得＋LLM＋通知）を検証する場合は、Staging（クラウド）で `EXTERNAL_MODE=real` を短期間だけ回す。

```
