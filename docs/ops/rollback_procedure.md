# ロールバック手順書

## API ロールバック（Cloud Run）

```bash
# 現在のリビジョン確認
gcloud run revisions list --service happynews-api --region asia-northeast1

# 前バージョンへトラフィックを切り替え
gcloud run services update-traffic happynews-api \
  --region asia-northeast1 \
  --to-revisions happynews-api-00001-xxx=100
```

## バッチロールバック（Cloud Run Job）

```bash
# 前バージョンのコンテナイメージ確認
gcloud artifacts docker images list asia-northeast1-docker.pkg.dev/PROJECT_ID/happynews/batch

# ジョブのコンテナイメージを更新
gcloud run jobs update happynews-batch \
  --image asia-northeast1-docker.pkg.dev/PROJECT_ID/happynews/batch:PREVIOUS_TAG \
  --region asia-northeast1
```

## 緊急撤退手順

### アプリの公開停止
1. Google Play Console → アプリ → リリース → 配信停止
2. Cloud Run サービスを停止: `gcloud run services delete happynews-api`

### データ保護
- Firestore データは自動バックアップ（Cloud Firestore エクスポート設定確認）
- バックアップ先: `gs://happynews-backup/`

## ロールバック判断基準

| 状況 | 対応 |
|------|------|
| API 5xx > 5% が 5分継続 | 即時ロールバック |
| バッチ2日連続失敗 | バッチロールバック + 原因調査 |
| クラッシュレート > 1% | アプリ更新停止 + 修正版リリース |
| データ不整合 | サービス停止 + データ修復 |
