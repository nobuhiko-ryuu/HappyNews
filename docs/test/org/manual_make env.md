了解。**“実機（スマホ）→ 同一LANのPCで動くDockerのAPI（http://PC_IP:8080）へ接続”**する最短ルートを、コピペ前提でまとめる。

前提（重要）：**スマホとPCが同じWi-Fi/LAN** にいること。別ネットだと届かない（DNS以前の物理）。

---

# 手順1：PC側でバックエンド（Docker）を LAN に公開して起動

## 1-1) 起動（backendディレクトリ）

```bash
cd backend
docker compose up --build -d
docker compose ps
```

## 1-2) “8080が外に出てるか”確認

`docker compose ps` の PORTS に `0.0.0.0:8080->8080/tcp` っぽい表示が出ていればOK。

もし `127.0.0.1:8080->8080/tcp` になってたら、実機からは絶対届かないので、`backend/docker-compose.yml` の ports がこうなってないか探す：

* ❌ `127.0.0.1:8080:8080`
* ✅ `8080:8080` もしくは `0.0.0.0:8080:8080`

修正後：

```bash
docker compose down
docker compose up --build -d
```

---

# 手順2：PCのLAN内IPを取得（スマホが叩く先）

## Windows（PowerShell / CMD）

```powershell
ipconfig
```

`IPv4 Address`（例：`192.168.0.10`）をメモ。

## macOS / Linux

```bash
ip a | grep -E "inet " | head
# もしくは
ifconfig | grep -E "inet " | head
```

ここでは仮に `PC_IP=192.168.0.10` とするね。

---

# 手順3：PCのファイアウォールを通す（ここで詰まりがち）

## Windows（PowerShell 管理者）

```powershell
New-NetFirewallRule -DisplayName "HappyNews API 8080" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

macOS/Linux は環境差があるけど、まずはOSのファイアウォールで **8080/TCP を許可**。

---

# 手順4：スマホから疎通確認（アプリより先に“通信できるか”を確定させる）

スマホのChromeで以下を開く：

* `http://192.168.0.10:8080/`

200/404どっちでもいい（**到達してレスポンスが返ること**が大事）。
もしタイムアウトなら、だいたいこれ：

* PCとスマホが同一LANじゃない
* ファイアウォール
* docker compose のポートが 127.0.0.1 バインド

---

# 手順5：Android側 BASE_URL を “PCのIP” に切り替える

どこでURLを持ってるかは実装次第なので、まず探索。

## 5-1) URL定義箇所を検索

```bash
cd android
rg -n "BASE_URL|baseUrl|localhost|10\.0\.2\.2|8080|run\.app|http://" .
```

見つかったところを、実機向けに変更：

* ❌ `http://localhost:8080`
* ❌ `http://10.0.2.2:8080`（エミュレータ専用）
* ✅ `http://192.168.0.10:8080`

> まずは**ベタ書き置換**が最短。あとでBuildConfig切替に整えるのは次の段階でOK。

---

# 手順6：debugビルドだけ “HTTP（cleartext）許可” を入れる

HTTPのままだと、Android 9+ でこう死ぬことがある：

* `CLEARTEXT communication not permitted`

最短で安全なのは **debug manifest overlay**。

## 6-1) 追加ファイル：`android/app/src/debug/AndroidManifest.xml`

（無ければ作る）

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:usesCleartextTraffic="true" />
</manifest>
```

これで **debugだけ** cleartext許可になる（releaseには入らない）。

---

# 手順7：再ビルド＆インストール

```bash
cd android
./gradlew :app:installDebug
```

アプリ起動 → Todayで通信が通るか確認。

---

## ありがちな落とし穴（ここだけ見ればだいたい勝てる）

* **BASE_URL が localhost / 10.0.2.2 のまま**（実機は届かない）
* dockerのポートが **127.0.0.1 バインド**（実機は届かない）
* **Windowsファイアウォールで8080が閉じてる**
* cleartext許可がなくて `CLEARTEXT... not permitted`

---

## 次の一手（あなたが貼ると一撃で仕留められる情報）

もしまだホームで `Unable to resolve host` / タイムアウト / 500 になるなら、以下のどれか1つ貼って：

1. Androidのエラーメッセージ全文（ホスト名が見えるやつ）
2. `docker compose ps` の PORTS 行
3. スマホChromeで `http://PC_IP:8080/` 開いた時の結果（タイムアウト or 何か返るか）

…で、原因を「ネットワーク/URL/HTTP許可/API側」のどれかに即断して、Claude Code向けの修正手順まで落とす。
