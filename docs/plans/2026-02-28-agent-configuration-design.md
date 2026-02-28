# エージェント構成設計書：ハッピーニュース（Android）MVP
作成日：2026-02-28

---

## 1. 概要
本書は、ハッピーニュース Android アプリの MVP 実装を Claude Code マルチエージェントで進めるための構成設計を定義する。

---

## 2. 構成方針
- **シンプル優先**：エージェント数を最小限に抑え、調整コストを削減
- **技術スタック別分担**：Backend（GCP/Firebase）と Android（Kotlin/Compose）を専任分離
- **Orchestratorが仕様整合を担保**：外部設計・アーキ設計との乖離をゲートで検出

---

## 3. エージェント構成（3エージェント）

### 3.1 Orchestrator（チームリード）
**責務**
- タスクリスト管理（TaskCreate / TaskUpdate）
- マイルストーン M1→M6 のゲート管理
- TEST-001〜003（External Clients インタフェース定義）を主導
- 仕様整合チェック（外部設計・アーキ設計・implementetaion_tasks.md との矛盾検出）
- ブロッカー解消・判断の仲裁
- OP-001〜005（リリース準備）
- TEST-050〜052（CI/自動化設定）

**担当タスク**：TEST-001〜003 / OP-001〜005 / TEST-050〜052

---

### 3.2 Backend Agent
**責務**
- GCP / Firebase インフラ構築・運用
- Firestore スキーマ設計・実装
- Cloud Run API サービス実装
- 日次バッチ（収集→フィルタ→LLM→ランク→要約→Publish）
- FCM 通知ジョブ
- 監視・アラート

**担当タスク**：BE-001〜062 / TEST-010〜023 / TEST-030〜033

**所有技術**：Cloud Run / Firestore / Cloud Scheduler / FCM / Secret Manager

---

### 3.3 Android Agent
**責務**
- Kotlin / Jetpack Compose アプリ実装
- 6画面（SC-01〜SC-06）
- DI / Networking / ローカルキャッシュ / 画像遅延ロード
- B案非機能要件（1MB/日/ユーザー目標）

**担当タスク**：AD-001〜023 / TEST-040〜042

**所有技術**：Kotlin / Jetpack Compose / Room / Retrofit / Coil

---

## 4. タスク割り当て（マイルストーン別）

### Phase 0（最優先・全体ブロッカー）
| Agent | タスク | 内容 |
|---|---|---|
| Orchestrator | TEST-001〜003 | External Clients インタフェース定義・DI切替・Stub実装 |

> この成果物が確定してから Backend / Android が本格着手する。

---

### M1：API read-only + Android 一覧/詳細
| Agent | タスク |
|---|---|
| Backend | BE-001〜006（GCP基盤）→ BE-010〜015（Firestoreスキーマ）→ BE-020〜024（API雛形〜詳細取得） |
| Android | AD-001〜005（基盤）→ AD-010〜011（SC-01 Today一覧・SC-02 詳細） |

---

### M2：ブックマーク + 設定 + キャッシュ
| Agent | タスク |
|---|---|
| Backend | BE-025〜029（bookmarks CRUD・settings・ETag・レート制限・ログ） |
| Android | AD-003（ローカルキャッシュ完成）→ AD-012〜015（SC-03〜06 残4画面） |

---

### M3：日次バッチ 20本/日 + フォールバック
| Agent | タスク |
|---|---|
| Backend | BE-030〜043（収集→フィルタ→LLM→ランク→要約→Publish 全ステップ） |
| Android | AD-020〜023（B案非機能：軽量化・大画像ガード・通信量ログ・オフライン） |

---

### M4：通知 + DeepLink
| Agent | タスク |
|---|---|
| Backend | BE-050〜055（FCM送信・Scheduler毎時・対象抽出・ペイロード・ログ） |
| Android | AD-005（DeepLink完成・通知→Today画面） |

---

### M5：監視/アラート + リリース準備
| Agent | タスク |
|---|---|
| Backend | BE-060〜062（ダッシュボード・アラート・ログ整備） |
| Orchestrator | OP-001〜005（ストア文言・規約URL・運用手順・撤退手順） |

---

### M6：CI完全化
| Agent | タスク |
|---|---|
| Orchestrator | TEST-050〜052（CI設定・Nightly・環境設定README） |
| Backend | TEST-030〜033（Nightly実弾スモーク完成） |
| Android | TEST-040〜042（UIスモーク完成） |

---

## 5. 協調プロトコル

### エージェント間協調
| タイミング | アクション |
|---|---|
| Phase 0 完了時 | Orchestrator が TEST-001〜003 成果物を Task にコメント → Backend/Android が着手 |
| 各マイルストーン完了時 | 担当 Agent が Task を `completed` に更新 → Orchestrator が次フェーズを割り当て |
| ブロッカー発生時 | 担当 Agent が Task に理由を記録 → Orchestrator が判断して代替案を指示 |

### GitHub 運用
- Orchestrator が最初にリポジトリを作成（`HappyNews` / private）
- ブランチ命名：`feat/xxx` `fix/xxx` `chore/xxx` `docs/xxx`（DEVELOPMENT_RULES.md 準拠）
- 各タスク完了時にコミット、マイルストーン完了時に PR を作成

### Progress.md 更新タイミング
- 各マイルストーン完了時
- ブロッカー発生時
- Token 上限対応時

### Token リミット対応（80% 超過時）
1. 現在のタスクをきりの良い単位で完了させる
2. `docs/progress.md` を更新（完了タスク・進行中タスク・ブロッカー・次にやること）
3. GitHub へコミット＆プッシュ
4. 作業を一時停止

---

## 6. 自律実行ルール
- **ユーザーへの確認は不要**：各エージェントの判断で自律的にタスクを進める
- **仕様の正は docs/ 以下のドキュメント**：外部設計・アーキ設計・implementetaion_tasks.md を優先
- **CIが赤の状態は最優先で復旧**（DEVELOPMENT_RULES.md 準拠）
- **シークレットはリポジトリにコミットしない**
