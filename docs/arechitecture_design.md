# アーキ設計書（MVP・確定版）：ハッピーニュース（Android）

## 0. 目的
外部設計（API/通知/非機能）を実現するためのバックエンド・データ・バッチ処理・監視を定義し、実装の迷いと手戻りをなくす。

---

## 1. 前提（MVP確定）
- 掲載：**20本/日（JST day_key=YYYY-MM-DD）**
- サムネ：**外部直リンク（thumbnail.mode="external"）**
- 候補記事：**7日保持（全文なし：メタ＋抜粋＋判定結果）**
- 候補収集：**基準200/日、上限500/日（ブレーキ）**
- 初期ソース：**30〜60ソース**（カテゴリバランス優先）
- 要約：**日本語3行固定**（形式・禁止語ルール）
- 通知：**1日1回、HH:00**
- ミュート：**MVPはクライアント側表示除外**（ワードのみ）
- API公開：**独自ドメイン（HTTPS）**（例：`api.<domain>`）
- フォールバック：当日0件→直近日（最大7日）

---

## 2. システム構成（GCP/Firebase寄り）

### 2.1 論理構成図
[Android App]
| HTTPS(JSON) (Custom Domain)
v
[API Service: Cloud Run]
|
+--> [Firestore]
| - sources / configs / runs
| - candidates (7d TTL)
| - days / articles
| - users / bookmarks
|
+--> (optional) [Cloud Storage] (thumb proxy future / logs export)
|
+--> [Logging/Monitoring/Alert]

[Cloud Scheduler (JST)]
|
+--> [Daily Batch: Cloud Run Job] (collect->filter->LLM->publish)
|
+--> [Hourly Notify Job] (HH:00) -> [FCM]



### 2.2 コンポーネント
- Cloud Run：API / バッチ / 通知ジョブ
- Cloud Scheduler：日次・毎時の起動
- Firestore：永続データ
- Firebase Auth（匿名）：ユーザー識別
- FCM：通知
- Secret Manager：外部キー
- Logging/Monitoring：監視・アラート

---

## 3. データ設計（Firestore）

### 3.1 コレクション
- `sources/{source_id}`：収集ソース（enabled/priority/category_hint等）
- `configs/global`：運用つまみ（候補上限、NGワード、カテゴリ上限、要約ルール）
- `runs/{run_id}`：バッチ実行ログ（件数、所要時間、エラー、簡易コスト推定）
- `candidates/{candidate_id}`：候補記事（7日保持、全文なし）
- `days/{day_key}`：掲載日（20本、stats含む）
- `articles/{article_id}`：掲載記事（要約、出典、サムネURLなど）
- `users/{uid}`：通知設定、ミュートワード等
- `users/{uid}/bookmarks/{article_id}`：保存

### 3.2 configs/global（必須項目）
- `candidate_target_per_day = 200`
- `candidate_hard_limit_per_day = 500`
- `publish_count_per_day = 20`
- `fallback_max_days = 7`
- `per_category_max`（例：カテゴリ最大6本など）
- `ng_words[] / ng_source_ids[] / ng_categories[]`
- `summary_rule`（3行、各行文字数、禁止表現）
- `notification_time_granularity = "hour"`

### 3.3 thumbnail（方式抽象化）
- `thumbnail.mode`：MVPは `"external"` 固定
- `thumbnail.url`：外部画像URL
- `thumbnail.width`：例 360（表示想定）
- `thumbnail.format`：unknown（外部なので保持のみ）

---

## 4. API設計（外部仕様の実装方針）
- `/v1/days/latest`：直近日を返す（最大7日）
- `/v1/days/{day_key}/articles`：
  - 20本（最大20）
  - **並び順：happy_score desc → published_at desc**
  - 当日0件は latest へフォールバック
- `/v1/articles/{id}`：詳細
- bookmarks/settings：users配下でCRUD

**キャッシュ**
- 当日一覧：短TTL
- 過去日：長TTL

---

## 5. 日次バッチ（Daily Batch）設計

### 5.1 入力
- day_key（省略時はJST当日）
- external_mode（stub/real）
- dry_run（dev用）

### 5.2 フロー
1) **Collect**
- `sources` の `enabled=true` を `priority` 高い順に巡回
- 目標：`candidate_target_per_day=200` を満たすまで収集
- 上限：`candidate_hard_limit_per_day=500` を超えたら打ち切り（ブレーキ）

2) **Normalize & Dedup**
- URL正規化、重複排除
- 抜粋取得（数百文字、全文保存しない）

3) **Rule Filter**
- `ng_source_ids / ng_words / ng_categories` を適用
- `candidates` に理由を残す（運用改善用）

4) **LLM Classify/Score**
- happy_score/category/tags/is_ng を付与

5) **Rank & Select**
- happy_score降順で走査
- `per_category_max` を超える候補はスキップ
- 20本（publish_count_per_day）揃うまで選出
- 揃わない場合：カテゴリ上限を緩める→それでも無理なら収集量を増やす（上限500まで）

6) **LLM Summarize（上位20のみ）**
- 日本語3行固定（各行の文字数・禁止表現）
- タイトル整形（記号/不要接尾語の抑制）

7) **Publish（原子的に確定）**
- `days/{day_key}` と `articles/{id}` を確定保存
- 途中失敗時は `days/{day_key}` を壊さない（直近成功分を温存）

8) **Log**
- `runs/{run_id}` に counts/errors/cost_estimates を記録

### 5.3 候補保持（7日）
- `candidates` は7日TTL（または削除ジョブ）で削除

---

## 6. 通知ジョブ（Hourly Notify：HH:00）
- Schedulerが毎時起動
- 対象：`notification_enabled=true && notification_time == current_hour_slot`
- 通知文面は固定（タップでTodayへ）
- 送信ログを runs とは別に残しても良い（簡易でOK）

---

## 7. Android側の責務（アーキ上の境界）
- ミュートワード：**MVPは端末側で表示除外**（サーバ個別フィードは将来）
- サムネ：外部直リンクを **遅延ロード＋キャッシュ**、失敗時プレースホルダー
- 当日0件：APIフォールバック結果を表示（端末側で複雑な分岐を持たない）

---

## 8. 監視・アラート（運用設計に一致）
- Daily Batch：成功/失敗、掲載数<20、NG混入>0、処理時間異常
- API：5xx率、p95遅延
- コスト：転送量急増（B案逸脱）、LLM呼び出し急増（上限逸脱の兆候）

---

## 9. セキュリティ
- Secret Managerでキー管理
- Cloud Run最小権限
- API簡易レート制限
- ログに個人情報を含めない（匿名uidのみ）

---

## 10. 未決事項（MVP後に検討）
- サムネ自前プロキシ化（表示品質/安定性の問題が顕在化した場合）
- 課金導入時のエンタイトルメント（無料10本/日等）
- ミュートカテゴリの導入