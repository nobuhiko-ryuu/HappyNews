# HappyNews テスト環境構築・実施手順（修正版）

## 1. 環境の種類

| 環境 | 概要 | 用途 |
|---|---|---|
| E0 | アプリ単体（バックエンド無し） | 起動・画面遷移・エラー耐性の確認 |
| E1 | ローカルDocker（Firestore Emulator） | API疎通・フォールバック・TTL・Today表示を安く速く検証 |
| E2 | Staging（Cloud Run + Firestore 縮小版） | E2E（バッチ→days生成→通知→deeplink）を本番近似で確認 |
| E3 | Prod（本番） | リリース前最終ゲート |

---

## 2. 共通前提（全環境）

### 2-1. 端末
- Android minSdk以上（Android 8.0+）
- Wi-Fi接続推奨
- 通知試験時は HappyNews を **バッテリー最適化しない**
- おやすみモード（DND）は通知試験時はOFF推奨

### 2-2. Firebase（Androidアプリが起動する最低条件）
- `android/app/google-services.json` 配置済み
- `android/app` に **Google Services plugin** 適用済み
- Firebase Console で **Anonymous Auth 有効化**
  - 理由: アプリ起動時に `signInAnonymously()` を実行するため

### 2-3. Androidビルド
- debugビルドで実機テストを実施する
- ローカルHTTP接続を行う場合は **debugだけ cleartext 許可**する

---

## 3. E0: アプリ単体（バックエンド無し）

### 3-1. 構築作業
構築作業なし。

### 3-2. 合格条件
- アプリが起動する
- バックエンド無しでもクラッシュしない
- Today は取得失敗でも画面が壊れない
- 再試行導線がある
- エラー文言が生ログ丸出しではなく、最低限ユーザー向けになっている

---

## 4. E1: ローカルDocker → 実機接続

## 4-1. Dockerバックエンドを起動

```bash
cd backend
docker compose up --build -d
docker compose ps
````

`PORTS` に `0.0.0.0:8080->8080/tcp` が表示されることを確認する。

### ポート設定の確認

`127.0.0.1:8080->8080/tcp` になっている場合、実機から届かないため `docker-compose.yml` の ports を修正する。

```yaml
# NG: 実機から届かない
ports:
  - "127.0.0.1:8080:8080"

# OK
ports:
  - "8080:8080"
```

修正後は再起動する。

```bash
docker compose down
docker compose up --build -d
```

---

## 4-2. Windows + Git Bash 利用時の注意

Windows の Git Bash では、Docker実行時に `/app` が勝手に Windows パスへ変換される場合がある。
そのため、`docker compose run` 実行時は以下の形式を使う。

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm -w /app -v "$(pwd -W):/app" api ...
```

PowerShell を使う場合はこの対策は不要。

---

## 4-3. 初期データ投入（seed）

### Windows Git Bash の場合

```bash
cd backend
MSYS_NO_PATHCONV=1 docker compose run --rm -w /app -v "$(pwd -W):/app" api python -m scripts.seed_firestore
```

### 成功条件

* `configs/global seeded`
* `sources seeded`

のようなログが出ること。

---

## 4-4. バッチ実行

```bash
cd backend
MSYS_NO_PATHCONV=1 docker compose run --rm -w /app -v "$(pwd -W):/app" api python -m app.batch.job
```

### 成功条件

* 候補収集 → フィルタ → 分類 → ランク → 要約 → publish が完了する
* `Published 20 articles` 相当のログが出る

---

## 4-5. テスト実行

```bash
cd backend
MSYS_NO_PATHCONV=1 docker compose run --rm -w /app -v "$(pwd -W):/app" api bash -lc "pip install -r requirements-dev.txt && pytest -q --ignore=tests/nightly"
```

### 成功条件

* nightly除外で全テスト成功すること

---

## 4-6. API疎通確認（PC上）

まずPC上でAPIが正しく応答することを確認する。

```bash
curl -sS http://localhost:8080/health
curl -sS http://localhost:8080/v1/days/latest
curl -sS "http://localhost:8080/v1/days/2026-03-03/articles"
```

### 期待結果

* `/health` → `{"status":"ok"}`
* `/v1/days/latest` → 最新の日付情報
* `/v1/days/<day_key>/articles` → articles を含むJSON

---

## 4-7. PCのLAN内IPを取得

### Windows（PowerShell）

```powershell
ipconfig
```

または、Wi-Fi / Ethernet の IPv4 だけを確認する場合:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.InterfaceAlias -match "Wi-Fi|Ethernet" -and $_.IPAddress -notlike "169.254.*" } |
  Select-Object InterfaceAlias,IPAddress
```

**Wi-FiまたはEthernetのIPv4アドレス** をメモする。
例: `192.168.0.10`

---

## 4-8. Windowsファイアウォール許可（管理者PowerShell）

```powershell
New-NetFirewallRule -DisplayName "HappyNews API 8080" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

確認:

```powershell
Get-NetFirewallRule -DisplayName "HappyNews API 8080" | Format-List -Property DisplayName,Enabled,Direction,Action
```

---

## 4-9. スマホから疎通確認

スマホのブラウザで以下を開く。

```text
http://<PC_WIFI_IP>:8080/health
```

例:

```text
http://192.168.0.10:8080/health
```

### 成功条件

* `{"status":"ok"}` が返ること

### 失敗時の確認ポイント

* スマホとPCが同一Wi-Fi（同一LAN）に接続されているか
* ゲストWi-Fiではないか
* Windowsファイアウォールで 8080 が許可されているか
* DockerのPORTSが `127.0.0.1` バインドになっていないか

---

## 4-10. Android の API_BASE_URL をローカル向けに変更

このプロジェクトでは、Android側の接続先は `android/app/build.gradle.kts` の `BuildConfig.API_BASE_URL` で管理する。

### 修正方針

* release は既存の本番向けURLのまま
* **debugだけ** ローカルDockerのIPへ向ける

### 例

```kotlin
buildTypes {
    debug {
        buildConfigField("String", "API_BASE_URL", "\"http://192.168.0.10:8080/\"")
    }
    release {
        isMinifyEnabled = false
        proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
    }
}
```

### 注意

* `localhost` は実機では使えない
* `10.0.2.2` はエミュレータ専用で、実機では使えない
* URL末尾の `/` は付ける

---

## 4-11. debugビルドだけ cleartext 許可

Android 9+ では HTTP通信がデフォルト拒否されるため、debugだけ cleartext を許可する。

ファイル: `android/app/src/debug/AndroidManifest.xml`
（無ければ新規作成）

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:usesCleartextTraffic="true" />
</manifest>
```

### 目的

* ローカルDockerの `http://<PC_WIFI_IP>:8080/` へ debugビルドだけ接続可能にする
* releaseビルドには影響させない

---

## 4-12. 再ビルド・再インストール

```bash
cd android
./gradlew :app:installDebug
```

必要なら一度アプリをアンインストールしてから再インストールする。

---

## 4-13. E1 の合格条件

* スマホでアプリが起動する
* Today画面で記事が取得できる
* 20本表示される
* Pull-to-refresh で再取得できる
* サムネイル読み込み失敗でも画面が崩れない
* 詳細画面へ遷移できる
* 保存/解除ができる
* 再起動後も保存状態が保持される

---

## 4-14. E1 よくある落とし穴

| 症状                                      | 原因                                                        |
| --------------------------------------- | --------------------------------------------------------- |
| タイムアウト                                  | PCとスマホが同一LANでない                                           |
| タイムアウト                                  | ゲストWi-Fi / AP隔離                                           |
| タイムアウト                                  | Windowsファイアウォールで8080が閉じている                                |
| タイムアウト                                  | Dockerのポートが `127.0.0.1` バインド                              |
| `CLEARTEXT communication not permitted` | debug Manifest の cleartext許可が未設定                          |
| `Unable to resolve host`                | API_BASE_URL が `localhost` / `10.0.2.2` のまま               |
| Todayが空                                 | seed / batch 未実行                                          |
| 起動直後クラッシュ                               | google-services plugin 未適用、または `google-services.json` 未配置 |

---

## 5. E2: Staging（GCP）

> 注記: この章は「実施方針・設計メモ」として扱う。
> そのままコピペで必ず通る完全手順ではなく、実際のプロジェクトID・認証設定・デプロイ方式に応じて具体化が必要。

---

## 5-1. GCP/Firebase プロジェクト作成（1回だけ）

```bash
gcloud projects create <staging-project-id>
gcloud config set project <staging-project-id>
```

### 注意

* プロジェクトIDはグローバル一意である必要がある
* Billing の紐付けが必要

必要なAPIを有効化する。

```bash
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com
```

Firestore は Native mode、リージョンは `asia-northeast1` を基本とする。

---

## 5-2. Secrets

```bash
# OpenAI APIキー
echo -n "<OPENAI_API_KEY>" | gcloud secrets create OPENAI_API_KEY --data-file=-

# Firebase Admin JSON
gcloud secrets create FIREBASE_ADMIN_JSON --data-file=/path/to/firebase-admin.json
```

---

## 5-3. 初期データ投入（configs/global, sources）

Firestore に以下を投入する。

### `configs/global`

| フィールド                           | Staging（縮小） | Prod（本番） |
| ------------------------------- | ----------- | -------- |
| `candidate_target_per_day`      | 50          | 200      |
| `candidate_hard_limit_per_day`  | 100         | 500      |
| `publish_count_per_day`         | 20          | 20       |
| `fallback_max_days`             | 7           | 7        |
| `notification_time_granularity` | `"hour"`    | `"hour"` |
| `summary_rule`                  | 設定          | 設定       |
| `per_category_max`              | 設定          | 設定       |
| `ng_words`                      | 最小限         | 本番値      |

### `sources`

* Staging: 5〜10件を `enabled=true`
* Prod: 30〜60件を `enabled=true`

投入スクリプトがある場合は `scripts/seed_firestore.py` を利用する。

---

## 5-4. Cloud Run デプロイ

```bash
# API
gcloud run deploy happynews-api-staging \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars EXTERNAL_MODE=real

# バッチ
gcloud run jobs create happynews-daily-batch-staging \
  --source . \
  --region asia-northeast1 \
  --set-env-vars EXTERNAL_MODE=real

# 通知
gcloud run jobs create happynews-notify-hourly-staging \
  --source . \
  --region asia-northeast1 \
  --set-env-vars EXTERNAL_MODE=real
```

必要に応じて Secrets を環境変数へマウントする。

```bash
gcloud run services update happynews-api-staging \
  --region asia-northeast1 \
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest
```

---

## 5-5. バッチ手動実行

```bash
gcloud run jobs execute happynews-daily-batch-staging --region asia-northeast1
```

### 確認

* Firestore `days/{today}` に article_ids が 20件あること

---

## 5-6. 通知ジョブ手動実行

```bash
gcloud run jobs execute happynews-notify-hourly-staging --region asia-northeast1
```

### 確認

* テスト端末に通知が届く
* 通知タップで Today へ遷移する
* deeplink 遷移でクラッシュしない

---

## 5-7. Scheduler（自動化）

```bash
gcloud scheduler jobs create http happynews-daily-scheduler \
  --schedule="0 1 * * *" \
  --uri="<実行先URL>" \
  --http-method=POST \
  --time-zone="Asia/Tokyo"
```

### 注意

* Stagingでは Scheduler は原則 OFF
* 必要な時だけ短時間 ON にする
* 検証後は必ず OFF に戻す
* 実際の Job 実行URLや認証設定は別途正確に詰める必要がある

---

## 6. Staging と Prod の差異

| 項目                            | Staging（検証）       | Prod（本番）       |
| ----------------------------- | ----------------- | -------------- |
| GCPプロジェクト                     | staging用          | prod用          |
| Firebase（FCM/Auth）            | staging用（テスト端末のみ） | prod用（実ユーザー）   |
| Firestore                     | staging用          | prod用          |
| Secrets                       | staging用キー        | prod用キー        |
| EXTERNAL_MODE                 | `real`（最終検証時）     | `real`         |
| sources                       | 5〜10件 enabled     | 30〜60件 enabled |
| candidate_target / hard_limit | 50 / 100          | 200 / 500      |
| Scheduler                     | 原則OFF（手動実行）       | ON             |
| 監視/アラート                       | 最低限               | フル             |

---

## 7. 事故防止ルール

* staging / prod は **FirebaseプロジェクトとFirestoreを必ず分ける**
* staging で自動SchedulerをONにするのは短期間だけにする
* 検証後は必ずOFFへ戻す
* 本番のソース追加は `enabled=true` 切替だけで反映できる運用を維持する
* release向け設定と debug向け設定を混在させない
* ローカルIPを build.gradle に直接入れた場合、作業後に元へ戻すことを忘れない

---

## 8. 実機テストの基本観点

### E0

* 起動
* 認証失敗時の復帰
* Todayのエラー耐性
* 画面遷移
* クラッシュしないこと

### E1

* Today 20本表示
* Pull-to-refresh
* 詳細画面
* 共有
* 保存/解除
* 再起動後保持
* フォールバック確認
* API接続エラー時のUI

### E2

* バッチ実行
* `days/{day_key}` 生成
* 通知送信
* 通知タップ deeplink
* HH:00 運用確認
* Stagingの縮小運用で問題ないこと

### E3

* Secrets
* 監視
* コストガード
* ストア文言
* 法務リンク
* 問い合わせ先
* リリース可否判定
