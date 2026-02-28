# 日次運用手順書

最終更新: 2026-02-28

## 毎日の確認事項

### 1. バッチ実行確認（JST 06:00 頃）
```bash
# Cloud Run ジョブの実行状況確認
gcloud run jobs executions list --job happynews-batch --region asia-northeast1 --limit 5

# 最新実行のログ確認
gcloud run jobs executions logs <execution-id> --region asia-northeast1
```

### 2. 記事配信確認
- Firestore Console で `days/{today_date}` ドキュメントを確認
- `article_ids` が 20 件あることを確認
- 不足の場合: フォールバック確認（前日分が使われているか）

### 3. API ヘルスチェック
```bash
curl https://happynews-api-xxxx-an.a.run.app/health
# {"status": "ok"} が返ること
```

### 4. モニタリングダッシュボード確認
- Cloud Console → Monitoring → HappyNews Dashboard
- 5xx エラー率 < 1% であること
- レイテンシ p99 < 2000ms であること

## 週次作業

### 新しいニュースソース追加
```python
# backend/scripts/add_source.py を使用
python -m scripts.add_source \
  --name "Source Name" \
  --feed-url "https://example.com/feed" \
  --homepage "https://example.com" \
  --language en \
  --country US \
  --category mixed \
  --priority 60
```

### NGワード更新
- Firestore Console → configs/global → ng_words フィールドを編集

## アラート対応

### バッチ失敗
1. ログ確認: `gcloud run jobs executions logs <id>`
2. 原因特定（RSS取得失敗 / OpenAI API エラー / Firestore 書き込みエラー）
3. 手動再実行: `gcloud run jobs run happynews-batch`
4. 前日記事で対応（フォールバック機能が自動動作）

### API 5xx 多発
1. Cloud Run ログ確認
2. Firestore 接続確認
3. 必要に応じて前バージョンにロールバック（下記参照）
