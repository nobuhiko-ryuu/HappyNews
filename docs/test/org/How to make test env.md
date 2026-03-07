うん、その理解でOK。
**Android側は実機で起動してチェックリスト通りに触れば検査できる**（ログ確認は必要に応じて）。
一方でバックエンドは「環境（Firestore/Secrets/ジョブ実行）を作って、手動でバッチとAPIを叩く」工程が必要になる。

以下、**最小コストで“バックエンドの動作確認環境”を作る手順**をまとめるね。
（あなたの構成：Cloud Run + Firestore + Scheduler + FCM + OpenAI）

---

# バックエンド検証環境の構築手順（最短ルート）

## 0) 目標（この手順で出来るようになること）

* `configs/global` と `sources` を投入できる
* 日次バッチを **手動で実行**して `days/{day_key}` に20本入るのを確認できる
* API を叩いて（latest/articles/detail）動作確認できる
* 通知ジョブを **手動で実行**して端末に通知が届くのを確認できる

---

## 1) 必要なもの

* Googleアカウント（GCPプロジェクトを作れる権限）
* ローカルPCに以下

  * `gcloud`（Google Cloud CLI）
  * `firebase`（Firebase CLI）※Auth/FCM/Emulator使う場合
  * Python（バックエンドがPythonなら。NodeならNode）
  * Docker（任意。あると楽）

> “本番相当の検証”なら Emulatorは必須じゃない。
> まずは **dev用のGCPプロジェクトを作って実環境で確認**が一番速い。

---

## 2) GCP/Firebaseのdevプロジェクト作成（1回だけ）

### 2-1. プロジェクト作成

```bash
gcloud projects create happynews-dev-<任意ID>
gcloud config set project happynews-dev-<任意ID>
```

### 2-2. 課金アカウント紐付け

Cloud Run / Firestore を使うなら、課金の有効化がほぼ必須。

* GCPコンソール → Billing → プロジェクトに紐付け

### 2-3. 必要APIを有効化

```bash
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com
```

### 2-4. Firestore作成（Native mode）

GCPコンソール → Firestore → 作成（Native）
リージョンは `asia-northeast1` などでOK（近いほど速い）。

---

## 3) Secrets（必須）

### 3-1. OpenAI APIキー

```bash
echo -n "<OPENAI_API_KEY>" | gcloud secrets create OPENAI_API_KEY --data-file=-
```

（既にある場合）

```bash
echo -n "<OPENAI_API_KEY>" | gcloud secrets versions add OPENAI_API_KEY --data-file=-
```

### 3-2. Firebase Admin（通知を本番相当で送る場合）

FCMをサーバから送るなら **Firebase Admin SDKのサービスアカウント鍵**が必要。

* Firebaseコンソール → プロジェクト設定 → サービスアカウント → 新しい秘密鍵を生成（JSON）

それを Secret Manager に入れる：

```bash
gcloud secrets create FIREBASE_ADMIN_JSON --data-file=/path/to/firebase-admin.json
```

---

## 4) データ初期投入（configs/global と sources）

あなたのアーキ仕様では

* `configs/global`
* `sources/{source_id}`（30〜60件）

が必須。

### 方法A：Firestoreコンソールで手入力（最短）

* Firestore → `configs` コレクション → doc `global` 作成
* 主要フィールドを入力
* `sources` コレクションに数件だけでも最初はOK（増やせる）

### 方法B：JSON投入スクリプト（安定・再現性高い）

（バックエンドに `scripts/seed_firestore.py` があるならそれを使う）
ない場合は、後でこちらで “投入用スクリプト雛形” を作れる。

**最低限入れる項目**

* `candidate_target_per_day=200`
* `candidate_hard_limit_per_day=500`
* `publish_count_per_day=20`
* `fallback_max_days=7`
* `per_category_max`（カテゴリ偏り制限）
* `ng_words`（最小）
* `notification_time_granularity="hour"`

---

## 5) Cloud Run（API）をデプロイ

### 5-1. デプロイ（例）

リポジトリにDockerfile/Cloud Buildがある前提。無ければ手元でビルドでもOK。

```bash
gcloud run deploy happynews-api \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars EXTERNAL_MODE=real
```

必要なら Secrets を環境変数としてマウント（プロジェクトの実装方式に合わせる）。
例（Secretを環境変数にする方式なら）：

```bash
gcloud run services update happynews-api \
  --region asia-northeast1 \
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest
```

---

## 6) 日次バッチ（Cloud Run Job）をデプロイ＆手動実行

### 6-1. Job デプロイ（例）

```bash
gcloud run jobs create happynews-daily-batch \
  --source . \
  --region asia-northeast1 \
  --set-env-vars EXTERNAL_MODE=real
```

### 6-2. 手動実行（まずここが最重要）

```bash
gcloud run jobs execute happynews-daily-batch --region asia-northeast1
```

**合格確認**

* Firestore `days/{today}` に20本
* `runs/{run_id}` の counts が正常（fetched>0、published=20）

---

## 7) Scheduler（自動化：任意、最後でOK）

手動で動くことを確認してからでいい。

```bash
gcloud scheduler jobs create http happynews-daily-scheduler \
  --schedule="0 1 * * *" \
  --uri="<CloudRunJob実行URL or Cloud Run endpoint>" \
  --http-method=POST \
  --time-zone="Asia/Tokyo"
```

※Cloud Run JobをHTTPで叩く方式は構成次第。
（Cloud Scheduler→Cloud Run Jobを直接起動する設計にしているなら、その手順に合わせる）

---

## 8) 通知ジョブ（手動で検証）

### 前提

* Androidが FCM token をサーバに登録していること
* サーバ側が token を `users` に保存していること

### 手動実行

```bash
gcloud run jobs execute happynews-notify-hourly --region asia-northeast1
```

**合格**

* 端末に通知が届く
* タップで Today へ遷移

---

# 9) ローカル（Emulator）でやりたい場合の最小手順（オプション）

あなたの現在の戦略では **nightlyにemulatorテスト**を置いてるので、必要なら：

1. firebase-tools を入れる
2. `firebase emulators:start --only firestore`
3. `FIRESTORE_EMULATOR_HOST=localhost:8080` を付けてテスト実行

ただし、**リリース前の動作確認としては dev GCP環境で回す方が確実**。

---

## 次にやると一気に楽になるもの

もし「configs/sources の投入」「ジョブ実行」「結果チェック」をもっと型にしたいなら、
あなたのリポジトリ構成に合わせて

* `scripts/seed_dev_firestore.(py|ts)`
* `scripts/run_dev_batch.sh`（day_key指定）
* `scripts/verify_day.sh`（published=20チェック）

を作ると、運用が超安定する。

---

もし今のバックエンドが「Cloud Run deployは済んでる・Firestoreもある」状態なら、あなたの現状に合わせて **最短の実行コマンドだけ**に絞って手順を書き直すよ。
