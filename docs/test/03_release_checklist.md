# リリース前チェックリスト

---

## 1. Staging最終検証

### 前提条件
- staging API / バッチ / 通知ジョブがデプロイ済み
- staging Firestore に `configs/global`（縮小値: 50/100）と `sources`（5〜10件）が入っている
- `EXTERNAL_MODE=real` で稼働中

### 日次バッチ確認
- [ ] `happynews-daily-batch-staging` を手動実行
- [ ] `days/{today}` が作成され、`article_ids` が **20件**
- [ ] `articles` が20件作られている
- [ ] `runs/{run_id}` の counts が妥当（fetched>0 / published=20）
- [ ] 3行要約が崩れていない（整形ガードが効いている）

### API確認
- [ ] `GET /v1/days/latest` が返る
- [ ] `GET /v1/days/{today}/articles` が20本返る
- [ ] 並び順: happy_score 降順 → published_at 降順
- [ ] 出典URLが有効で、アプリから開ける

### 通知確認
- [ ] Android（staging版）で通知ON・次のHH:00に設定
- [ ] staging通知ジョブを手動実行
- [ ] 端末に通知が届き、タップでTodayへ遷移する

---

## 2. Android アプリ最終確認

### 起動・認証
- [ ] 初回起動で匿名ログイン → Todayが表示される
- [ ] ログイン失敗時に "Failed→再試行" で復帰できる
- [ ] 機内モード/圏外で起動しても落ちない・適切な案内が出る

### Today一覧（SC-01）
- [ ] 20本表示される（当日 or 直近日フォールバック）
- [ ] スクロールが軽い（カクつき・固まりなし）
- [ ] サムネが取得できない記事もプレースホルダーで崩れない
- [ ] Pull to refresh が動作する

### 記事詳細（SC-02）
- [ ] タイトル・3行要約・タグ・出典が表示される
- [ ] 出典リンクで外部ブラウザが開く
- [ ] 共有でOS共有シートが出る

### 保存（SC-03）
- [ ] 一覧/詳細から保存トグルができる
- [ ] 保存一覧に反映され、再起動後も保持される
- [ ] 解除できる

### 設定（SC-04/05/06）
- [ ] 通知 ON/OFF が効く
- [ ] 通知時刻（HH:00）の変更が保存される
- [ ] OS通知権限が未許可のとき案内と設定誘導が正しい
- [ ] 法務/情報画面が開き、リンクが正しい

### ミュートワード
- [ ] ミュートワードの追加/削除ができる
- [ ] ミュート対象が一覧で非表示になる（クライアントフィルタ）

---

## 3. バックエンド最終確認

- [ ] sources（enabled）から収集して候補が作られる
- [ ] 候補収集が200を目標に進み、500で打ち切られる（hard_limit）
- [ ] Rule Filter が働く（NGワード/NGソースが弾かれる）
- [ ] LLM分類が動く（happy_score / category / tags / is_ng が付く）
- [ ] ランキングで20本が選定される（カテゴリ偏りが極端でない）
- [ ] 要約が必ず3行になっている（禁止語混入なし）
- [ ] `days/{day_key}` に **20本** 入る
- [ ] 当日分が無い/バッチ失敗時に `latest` が直近日（最大7日）を返す
- [ ] candidates に `ttl_delete_at` が入っている（datetime型）
- [ ] バッチ成功/失敗がログで追える

---

## 4. 統合テスト

- [ ] FCMトークンがバックエンドに登録される
- [ ] 通知ONにして設定したHH:00に通知が届く
- [ ] 通知タップでTodayへ遷移する（deeplink）
- [ ] 通知OFFで届かないことを確認
- [ ] LLM/APIキーが無効のとき: バッチが落ちてもアプリは直近日を出す（壊れない）

---

## 5. リリース直前チェック

- [ ] 本番のSecrets/設定値がprodに入っている（devを向いていない）
- [ ] `configs/global` のNGワード/カテゴリ上限が過激すぎない（20本埋まらなくなっていない）
- [ ] 1日分の運用を手動で回せる手順がある（day_key指定・再実行）
- [ ] ストア文言/法務リンク/問い合わせ先が正しい
- [ ] prod Secrets（OpenAI/FCM admin）が正しいキーになっている
- [ ] prod `configs/global` が本番値（candidate_target=200 / hard_limit=500）になっている
- [ ] prod sources が30〜60件 enabled になっている
- [ ] 監視/アラートが有効
- [ ] `EXTERNAL_MODE=real` で稼働している

---

## 6. Prod本番開始手順（推奨順序）

1. daily batch Scheduler を ON（毎日）
2. 1日分が安定して20本出るのを確認
3. notify hourly Scheduler を ON（毎時）
