# 手順書：テスト検証環境（Staging）と本番環境（Prod）の切り分けと運用
対象：ハッピーニュース（Android）  
目的：本番に近い検証を安全・低コストで行い、誤送信/誤書込を防ぐ

---

## 1. 基本方針（結論）
- **コードは同一**（同じコミット/同じDockerイメージ）を Staging/Prod にデプロイ
- **差分は設定とデータのみ**（GCP/Firebase/Secrets/configs/sources/スケジュール）
- Stagingは **“本番縮小版”**：外部依存は real で動かすが、規模を絞ってコストと事故を抑える

---

## 2. StagingとProdの違い（一覧）
| 項目 | Staging（検証） | Prod（本番） |
|---|---|---|
| GCPプロジェクト | staging用（本番と分離） | prod用 |
| Firebaseプロジェクト（FCM/Auth） | staging用（テスト端末だけ） | prod用（実ユーザー） |
| Secrets | staging用（キー別） | prod用 |
| EXTERNAL_MODE | `real`（最終検証時）/ 普段は`stub`でも可 | `real` |
| sources | **5〜10件だけenabled**（縮小） | 30〜60件enabled（拡張可） |
| candidate_target/hard_limit | **小さく**（例：50/100） | **本番値**（200/500） |
| publish_count_per_day | 20（本番と同じ） | 20 |
| Scheduler | 原則OFF（手動実行） | ON（毎日/毎時） |
| 監視/アラート | 最低限（失敗検知） | 本番フル（失敗/件数/コスト） |

---

## 3. 事前準備（1回だけ）

### 3.1 プロジェクト分離
- [ ] GCPプロジェクトを2つ用意：`happynews-staging`, `happynews-prod`
- [ ] Firebaseプロジェクトを2つ用意：`happynews-staging`, `happynews-prod`
  - Auth（匿名）有効化
  - Cloud Messaging（FCM）有効化
  - stagingには **テスト端末だけ** を使う

### 3.2 Secrets（staging/prod別）
- [ ] `OPENAI_API_KEY`（staging用 / prod用）
- [ ] `FIREBASE_ADMIN_JSON`（staging用 / prod用）
  - Firebaseコンソール → サービスアカウント → 秘密鍵JSON を発行して登録

### 3.3 Firestore
- [ ] staging/prodそれぞれで Firestore（Native）を作成
- [ ] TTLを使う場合：
  - `candidates.ttl_delete_at` を TTLフィールドとして有効化（staging/prod両方）

---

## 4. デプロイ（共通手順）
> 重要：**同じコミット/同じイメージ**を staging/prod にデプロイする

### 4.1 API（Cloud Run Service）
- [ ] staging：`happynews-api-staging`
- [ ] prod：`happynews-api-prod`
- 環境変数：
  - `EXTERNAL_MODE=real`（stagingの最終検証期間／prodは常時）
  - 普段のstaging開発は `stub` でも可

### 4.2 バッチ（Cloud Run Job）
- [ ] staging：`happynews-daily-batch-staging`
- [ ] prod：`happynews-daily-batch-prod`
- 環境変数：
  - `EXTERNAL_MODE=real`（staging最終検証／prod常時）

### 4.3 通知ジョブ（Cloud Run Job）
- [ ] staging：`happynews-notify-hourly-staging`
- [ ] prod：`happynews-notify-hourly-prod`
- stagingはテスト端末のみ通知されること

---

## 5. 初期データ投入（staging/prod）
> この章が「本番に近づける/遠ざける」を決めるレバー

### 5.1 configs/global（共通の基本形）
必須（両環境）：
- `publish_count_per_day = 20`
- `fallback_max_days = 7`
- `notification_time_granularity = "hour"`
- `summary_rule`（3行/禁止語など）
- `per_category_max`（カテゴリ偏り制御）

### 5.2 configs/global（差分：候補収集量）
#### Staging（縮小）
- `candidate_target_per_day = 50`
- `candidate_hard_limit_per_day = 100`

#### Prod（本番）
- `candidate_target_per_day = 200`
- `candidate_hard_limit_per_day = 500`

### 5.3 sources（差分：enabledの数）
#### Staging（縮小）
- まず **5〜10ソース**のみ `enabled=true`
- それ以外は `enabled=false`

#### Prod（本番）
- **30〜60ソース** `enabled=true`
- 追加/削除の運用を回す

---

## 6. Staging（リリース前）検証の実行手順
> ここが“本番に近いか”を保証するための最重要手順

### 6.1 前提
- staging API/バッチ/通知ジョブがデプロイ済み
- staging Firestoreに `configs/global` と縮小 `sources` が入っている
- `EXTERNAL_MODE=real` にしている（最終検証期間）

### 6.2 日次バッチ（手動実行）
- [ ] `happynews-daily-batch-staging` を **手動実行**
- [ ] Firestoreで確認：
  - `days/{today}` が作成される
  - `article_ids` が **20件**
  - `articles` が20件作られている
  - `runs/{run_id}` の counts が妥当（fetched>0 / published=20）

**合格条件**
- 20本が埋まる
- 3行要約が崩れない（3行ガードの効き確認）

### 6.3 API確認（最低3本）
- [ ] `GET /v1/days/latest` が返る
- [ ] `GET /v1/days/{today}/articles` が20本返る
- [ ] 並び順：happy_score desc → published_at desc
- [ ] 出典URLが有効で、アプリから開ける

### 6.4 通知（手動→自動の順）
#### まず手動
- [ ] Android（staging版）で通知ON＋通知時刻を次のHH:00に設定
- [ ] staging通知ジョブを **手動実行**
- [ ] 端末に通知が届き、タップでTodayへ遷移する

#### 次に自動（必要な場合のみ短期間）
- [ ] staging Scheduler を一時的にON（毎時）
- [ ] 期待時刻に通知が届くことを確認
- [ ] 検証後、SchedulerをOFFへ戻す

---

## 7. Prod（リリース後）運用手順
### 7.1 本番の開始前チェック
- [ ] prod secrets（OpenAI/FCM admin）が正しい
- [ ] prod configs/global が本番値（200/500）になっている
- [ ] prod sources が 30〜60 enabled
- [ ] 監視/アラートが有効
- [ ] `EXTERNAL_MODE=real` で動いている

### 7.2 SchedulerをONにする順序（推奨）
1) daily batch をON（毎日）  
2) 1日分が安定して20本出るのを確認  
3) notify hourly をON（毎時）

---

## 8. 事故防止のルール（重要）
- stagingとprodは **Firebaseプロジェクトを分ける**（誤通知防止）
- stagingとprodは **Firestoreを分ける**（誤データ混入防止）
- stagingで自動スケジュールをONにするのは **短期間だけ**
- 本番のソース追加は「enabled=true」にするだけで反映できる運用にする

---

## 9. “本番に十分近い” の合格ライン（最終判断）
Staging（EXTERNAL_MODE=real）で以下が通れば、Prodでも高確率で同様に動く：
- 日次バッチが **20本**を安定生成できる
- 3行要約が崩れない（3行ガードが効く）
- 通知が届く→タップでTodayへ遷移する
- 当日0件でもlatestへフォールバックできる（最大7日）

---