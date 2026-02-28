# IMPLEMENTATION_TASKS.md（MVP・確定版）
実装タスク分割（統合版）：ハッピーニュース（Android）

---

## 0. ゴール（MVP受け入れ基準）
- 毎日JSTで**20本**が自動生成され、Androidアプリで閲覧できる
- 画面：一覧/詳細/保存/共有/設定/通知ON-OFF/通知時刻（HH:00）が動作する
- 当日0件時は直近日（**最大7日**）へフォールバック
- B案：**1MB/日/ユーザー目標**に沿う（遅延ロード/キャッシュ）
- 外部依存を含むが **CIは外部ゼロ**で高速に回る（実弾は夜間スモーク）

---

## 1. 実装方針（確定）
- サムネ：外部直リンク（thumbnail.mode="external"）
- 候補記事：7日保持（全文なし）
- 候補収集：基準200/日、上限500/日（ブレーキ）
- 初期ソース：30〜60、`sources` で管理（enabled/priority）
- configs/global に運用つまみ集約（NG・カテゴリ上限・要約ルール）
- 通知：HH:00（時単位）
- ミュート：クライアント側表示除外（ワードのみ）

---

## 2. 共通：外部依存分離（Interface化）※最優先
- [ ] (TEST-001) External Clients インタフェース定義（Fetcher/LLM/FCM/Thumb）
- [ ] (TEST-002) DIで `stub/real` 切替（local/ci/dev/prod）
- [ ] (TEST-003) スタブ実装（固定RSS/固定LLM応答）

成果物：外部ゼロで全テスト安定

---

## 3. バックエンド

### 3.1 基盤
- [ ] (BE-001) GCP/Firebaseプロジェクト（dev/prod）
- [ ] (BE-002) Firestore有効化
- [ ] (BE-003) Cloud Run有効化・最小権限SA
- [ ] (BE-004) Secret Managerにキー登録
- [ ] (BE-005) 独自ドメイン(HTTPS) `api.<domain>`
- [ ] (BE-006) Logging/Monitoring土台

### 3.2 Firestoreスキーマ（確定版）
- [ ] (BE-010) コレクション作成：sources/configs/runs/candidates/days/articles/users/bookmarks
- [ ] (BE-011) 必要インデックス作成（通知抽出・latest取得など）
- [ ] (BE-012) **候補保持B固定：candidatesを7日TTL運用**（全文なし）
- [ ] (BE-013) `configs/global` の初期投入（200/500/20/7、NG、カテゴリ上限、要約ルール）
- [ ] (BE-014) `sources` の初期投入（30〜60、enabled/priority/category_hint）
- [ ] (BE-015) セキュリティルール（匿名ユーザーは自分の設定/ブクマのみ）

### 3.3 API Service（Cloud Run）
- [ ] (BE-020) API雛形（バリデーション/エラー）
- [ ] (BE-021) JST day_keyユーティリティ
- [ ] (BE-022) GET `/v1/days/latest`（最大7日フォールバック）
- [ ] (BE-023) GET `/v1/days/{day_key}/articles`
  - 並び順：happy_score desc → published_at desc
  - 0件→latestへフォールバック
- [ ] (BE-024) GET `/v1/articles/{id}`
- [ ] (BE-025) bookmarks CRUD
- [ ] (BE-026) settings PUT（notification_enabled、notification_time(HH:00)、mute_words）
- [ ] (BE-027) ETag/Cache-Control（当日短TTL、過去長TTL）
- [ ] (BE-028) 簡易レート制限（UID/IP）
- [ ] (BE-029) 構造ログ（request_id等）

### 3.4 日次バッチ（Daily Batch）
- [ ] (BE-030) Cloud Run Job雛形（idempotent）
- [ ] (BE-031) Scheduler（日次・JST）
- [ ] (BE-032) 手動実行（day_key指定、dry_run）
- [ ] (BE-033) Collect：sources(enabled)をpriority順に巡回
  - target=200、hard_limit=500（configs/global参照）
- [ ] (BE-034) Normalize/Dedup（URL正規化、重複排除）
- [ ] (BE-035) Excerpt取得（数百文字、全文保存しない）
- [ ] (BE-036) Rule Filter（configs/globalのNG群）
- [ ] (BE-037) LLM軽判定（score/category/tags/is_ng）
- [ ] (BE-038) Rank：カテゴリ上限（configs/global per_category_max）
- [ ] (BE-039) LLM要約：上位20のみ（3行固定＋禁止表現）
- [ ] (BE-040) ガードレール：上限/タイムアウト/リトライ
- [ ] (BE-041) Publish：days/articlesを原子的に確定（失敗で壊さない）
- [ ] (BE-042) runs記録（counts/errors/cost_estimates）
- [ ] (BE-043) candidates TTL確認（7日）

### 3.5 通知（FCM：HH:00）
- [ ] (BE-050) FCM送信サービス
- [ ] (BE-051) Scheduler：毎時起動
- [ ] (BE-052) 対象抽出（enabled & time slot）
- [ ] (BE-053) ペイロード（DeepLink→Today）
- [ ] (BE-054) 送信ログ
- [ ] (BE-055) 軽量リトライ

### 3.6 監視・アラート
- [ ] (BE-060) ダッシュボード（バッチ、掲載数、NG混入、API 5xx、p95）
- [ ] (BE-061) アラート（バッチ失敗、掲載<20、NG>0、コスト急増）
- [ ] (BE-062) ログ整備

---

## 4. Android

### 4.1 基盤
- [ ] (AD-001) DI/Networking/DB構成
- [ ] (AD-002) APIクライアント（タイムアウト/リトライ）
- [ ] (AD-003) ローカルキャッシュ（当日一覧、設定、ブクマ）
- [ ] (AD-004) 画像ロード（遅延ロード＋キャッシュ、失敗時プレースホルダー）
- [ ] (AD-005) Deep Link（通知→Today）

### 4.2 画面
- [ ] (AD-010) SC-01 Today一覧（20本、保存トグル、Pull、フォールバック表示）
- [ ] (AD-011) SC-02 詳細（保存/共有/出典リンク）
- [ ] (AD-012) SC-03 保存一覧
- [ ] (AD-013) SC-04 設定（ミュートワード、法務入口）
- [ ] (AD-014) SC-05 通知設定（ON/OFF、時刻HH:00選択、OS設定誘導）
- [ ] (AD-015) SC-06 法務/情報

### 4.3 非機能（B案）
- [ ] (AD-020) 一覧レンダリング軽量化
- [ ] (AD-021) 大画像のガード（表示サイズ固定）
- [ ] (AD-022) 通信量ガードログ（画像平均サイズ/枚数）
- [ ] (AD-023) オフライン時（キャッシュ表示）

---

## 5. テスト（コスパ/タイパ最適化）

### 5.1 毎PR：外部ゼロ
- [ ] (TEST-010) Firestore Emulator整備
- [ ] (TEST-011) API契約テスト（並び順・フォールバック含む）
- [ ] (TEST-012) バッチ統合テスト（idempotent、掲載=20、原子性）
- [ ] (TEST-040) Android UIスモーク（主要導線）
- [ ] (TEST-041) オフライン/タイムアウト
- [ ] (TEST-042) 画像遅延ロード/キャッシュ

### 5.2 ゴールデンセット（回帰の核）
- [ ] (TEST-020) ゴールデン候補JSON（重複/NG/偏り/多言語）
- [ ] (TEST-021) 制約ベースの期待定義（3行、禁止語、タグ数、score範囲）
- [ ] (TEST-022) ルール/ランキング回帰
- [ ] (TEST-023) 失敗ケース追加運用

### 5.3 Nightly（dev）：実弾スモーク（上限固定）
- [ ] (TEST-030) LLM実弾スモーク（ゴールデン20件固定）
- [ ] (TEST-032) 収集実弾スモーク（厳選3ソース、soft fail）
- [ ] (TEST-033) 通知実弾スモーク手順（リリース前）

### 5.4 CI/自動化
- [ ] (TEST-050) CI（毎PR）：ユニット＋Emulator統合＋UIスモーク
- [ ] (TEST-051) Nightly：LLM/収集スモーク
- [ ] (TEST-052) local/ci/dev/prod 設定表をREADME化

---

## 6. リリース準備・運用
- [ ] (OP-001) ストア掲載文/スクショ文言
- [ ] (OP-002) 規約/PP URL
- [ ] (OP-003) 運用手順（毎日/毎週/毎月）
- [ ] (OP-004) 撤退手順
- [ ] (OP-005) sources/ng_words更新手順

---

## 7. マイルストーン
- M1：API read-only + Android一覧/詳細（保存なし）
- M2：ブクマ + 設定（通知ON/OFF/HH:00/ミュート）+ キャッシュ
- M3：日次バッチで20本/日生成 + 最大7日フォールバック
- M4：通知（毎時）+ DeepLink
- M5：監視/アラート + リリース準備
- M6：CI外部ゼロ + Nightly実弾スモーク

---