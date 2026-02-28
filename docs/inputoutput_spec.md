# ソース管理・日次バッチ 入出力仕様（MVP確定）
対象：ハッピーニュース（Android）MVP / B案（軽サムネ）/ 掲載20本/日

## 0. ここで確定した仕様（MVP）
- サムネ：MVPは **外部直リンク**（thumbnail.mode="external"）
- 候補記事：**7日保持（B案）**（全文は保存しない。メタ＋抜粋＋判定結果のみ）
- 通知時刻：**時単位（HH:00）**
- 候補収集：**基準200/日、上限500/日（ブレーキ付き）**
- 初期ソース：**30〜60ソース**（カテゴリバランス優先）
- 要約：**日本語3行固定**（形式・禁止表現ルールあり）

---

## 1. Firestoreコレクション設計（ソース管理 + バッチ運用）

### 1.1 コレクション一覧
- `sources/{source_id}` … 収集元（RSS等）の定義
- `source_groups/{group_id}`（任意）… ソースのグルーピング（ジャンル/優先度など）
- `configs/global` … 共通設定（候補上限、カテゴリ上限、NGワードなど）
- `runs/{run_id}` … バッチ実行ログ（再実行・原因追跡用）
- `candidates/{candidate_id}` … 候補記事（7日保持）
- `days/{day_key}` … 掲載日（20本）確定データ
- `articles/{article_id}` … 掲載記事（要約＋リンク）

> 既存の `users/{uid}` `users/{uid}/bookmarks` はそのまま（別章で済）

---

## 2. `sources/{source_id}` 仕様（初期ソース管理の核）

### 2.1 主キー
- `source_id`: 英数+ハイフン推奨（例：`gdn`, `positive-news`）

### 2.2 フィールド定義
必須：
- `name`: string（表示名）
- `type`: string（`rss` | `api` | `html`）※MVPは `rss` のみ想定
- `feed_url`: string（RSS URL）
- `homepage_url`: string（サイトURL）
- `enabled`: boolean（trueで収集対象）
- `priority`: number（1〜100、MVPは 50 を標準。高いほど先に収集）
- `language_hint`: string（例：`en` `ja`、不明なら`unknown`）
- `country_hint`: string（例：`US` `JP`、不明なら`unknown`）
- `category_hint`: string（後述のカテゴリセットから。`mixed`可）
- `created_at`, `updated_at`: timestamp

運用用（推奨）：
- `fetch_interval_minutes`: number（例：180。MVPは日次でもOK）
- `last_fetched_at`: timestamp
- `consecutive_failures`: number（連続失敗回数）
- `quarantined`: boolean（trueなら一時停止扱い）
- `notes`: string（運用メモ）

品質コントロール（推奨）：
- `trust_score`: number（0〜100、初期は50固定でも良い）
- `allow_tags`: string[]（このソースはこのタグが強い等。任意）
- `deny_patterns`: string[]（URLパターンや単語でソース内除外。任意）

### 2.3 カテゴリセット（MVP）
固定セットを先に決める（後から増やすとランキングが壊れやすい）。
- `science`（科学/宇宙）
- `health`（医療/健康の前進）
- `environment`（環境/保全/再生）
- `animals`（動物）
- `education`（教育/学び）
- `community`（地域/福祉/助け合い）
- `technology`（テックの前向き活用）
- `sports`（前向き結果 ※炎上/スキャンダルはNG）
- `culture`（文化/アート）
- `mixed`（混在）

---

## 3. `configs/global`（運用で変えたい“つまみ”を集約）

### 3.1 推奨フィールド
- `candidate_target_per_day`: 200
- `candidate_hard_limit_per_day`: 500
- `publish_count_per_day`: 20
- `fallback_max_days`: 7
- `per_category_max`: map（例：1カテゴリ最大6本など）
- `ng_words`: string[]（MVPのNGワードリスト）
- `ng_source_ids`: string[]
- `ng_categories`: string[]
- `summary_rule`: object
  - `lines`: 3
  - `chars_per_line_min`: 25
  - `chars_per_line_max`: 40
  - `banned_phrases`: string[]（煽り語）
- `notification_time_granularity`: `"hour"`（将来 `"15min"`）

> ここを編集すると挙動が変わるので、編集は最小の管理画面 or 手動更新でOK。

---

## 4. `runs/{run_id}`（バッチ実行ログ：再現性・原因追跡の心臓）

### 4.1 run_id
- 形式例：`run_2026-03-01_01`（day_key＋連番）
- 再実行時は連番で増やす（`_02` etc）

### 4.2 フィールド例
- `day_key`: string
- `mode`: string（`dev`|`prod`）
- `external_mode`: string（`stub`|`real`）
- `status`: string（`running`|`succeeded`|`failed`）
- `started_at`, `finished_at`
- `counts`: object
  - `fetched`: number
  - `deduped`: number
  - `rule_filtered`: number
  - `llm_scored`: number
  - `summarized`: number
  - `published`: number
  - `ng_detected`: number
- `cost_estimates`: object（任意）
  - `llm_calls`: number
  - `llm_tokens_in`: number
  - `llm_tokens_out`: number
- `errors`: array（code/message/step）
- `source_stats`: map（source_id→ fetched_count/failed etc）

---

## 5. `candidates/{candidate_id}`（7日保持：全文なし）

### 5.1 candidate_id
- 推奨：`hash(normalized_url)`（衝突回避に source_id も混ぜる）

### 5.2 フィールド（最小）
- `day_key`
- `source_id`
- `source_name`
- `original_url`
- `title`
- `excerpt`（数百文字まで）
- `published_at`
- `collected_at`
- `lang`
- `rule_filtered`: boolean
- `rule_filter_reasons`: string[]
- `llm`（object）
  - `happy_score`
  - `category`
  - `tags[]`
  - `is_ng`
- `ttl_delete_at`（TTL運用するなら）

---

## 6. 日次バッチ：入出力仕様（I/O）

### 6.1 入力（バッチ起動パラメータ）
- `day_key`（省略時はJSTの当日を採用）
- `mode`：`dev`/`prod`
- `external_mode`：`stub`/`real`
- `limits`（省略時は configs/global）
  - `candidate_target_per_day`（デフォ200）
  - `candidate_hard_limit_per_day`（上限500）
  - `publish_count_per_day`（20）
- `dry_run`：boolean（trueならPublishしない。devスモーク用）

### 6.2 出力（成功時）
- `days/{day_key}` を確定作成（published_at、article_ids、stats）
- `articles/{article_id}` を20本作成
- `runs/{run_id}` を `succeeded` で確定
- `candidates/` を（B案採用のため）保存し、7日運用

### 6.3 Idempotency（再実行ルール）
- 同一 `day_key` で再実行するときは：
  - `runs` に新規run_idで記録
  - `days/{day_key}` は「staging→確定の置換」で一貫性を担保
  - 途中失敗したら `days/{day_key}` を壊さない（直近成功分を温存）

---

## 7. ランキング選定ルール（MVPの“安定の芯”）
目的：20本の品質とカテゴリバランスを守る

推奨ルール（シンプル版）：
1) `rule_filtered=false` かつ `llm.is_ng=false` のみ対象
2) happy_score降順
3) カテゴリ上限 `per_category_max` を超えたらスキップ
4) 20本埋まるまで走査
5) 埋まらない場合：
   - カテゴリ上限を一段緩める（例：+1）
   - それでも無理なら候補収集を増やす（上限500まで）

---

## 8. 要約仕様（3行固定：形式ルール）
- **必ず3行**（改行2つ）
- 各行 **25〜40文字目安**
- 構成：
  1. 何が起きたか（結論）
  2. 具体（誰が/どこで/何が良い）
  3. 前向きな意味（改善/進捗/希望）
- 禁止：
  - 煽り語（衝撃/炎上/閲覧注意 等）
  - 悲惨さの強調
  - 根拠のない断定（完全解決 等）

---

## 9. サムネ仕様（MVP：外部直リンク）
- `thumbnail.mode="external"`
- `thumbnail.url` は元サイト画像URL
- Android側で遅延ロード＋キャッシュ、失敗時はプレースホルダー
- 将来、プロキシ方式へ移行可能（mode切替）

---

## 10. 初期ソース運用（30〜60で開始）
- ソースはカテゴリバランスを意識して投入（mixed頼みを減らす）
- `consecutive_failures` が閾値を超えたら `quarantined=true`
- 追加/削除は `sources` の更新だけで反映（バッチはenabledのみ参照）

---

# 付録：サンプルドキュメント

## sources/{source_id} 例
{
  "name": "Example Good News",
  "type": "rss",
  "feed_url": "https://example.com/feed",
  "homepage_url": "https://example.com",
  "enabled": true,
  "priority": 60,
  "language_hint": "en",
  "country_hint": "US",
  "category_hint": "community",
  "fetch_interval_minutes": 180,
  "consecutive_failures": 0,
  "quarantined": false,
  "trust_score": 55,
  "created_at": "...",
  "updated_at": "..."
}

## configs/global 例
{
  "candidate_target_per_day": 200,
  "candidate_hard_limit_per_day": 500,
  "publish_count_per_day": 20,
  "fallback_max_days": 7,
  "per_category_max": {
    "science": 6,
    "health": 6,
    "environment": 6,
    "animals": 6,
    "community": 6,
    "mixed": 8
  },
  "notification_time_granularity": "hour",
  "summary_rule": {
    "lines": 3,
    "chars_per_line_min": 25,
    "chars_per_line_max": 40,
    "banned_phrases": ["衝撃", "炎上", "閲覧注意"]
  }
}