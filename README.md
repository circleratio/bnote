# bnote

Python の軽量 Web フレームワーク [Bottle](https://bottlepy.org/) で作られた、シンプルなメモ（ノート）管理アプリケーションです。日々のメモや、運動などの行動記録を SQLite データベースに保存し、ブラウザから閲覧・編集できます。

## 概要

- **メモの登録**: 自由記述のテキストメモ（`note` タイプ）と、あらかじめ用意された選択肢からの行動記録（`action` タイプ）を登録できます。
- **一覧表示**: 当日分の一覧、日付指定の一覧、全件のページネーション付き一覧（1 ページ 50 件）を表示します。
- **前日・翌日への移動**: 日付一覧画面から前後の日付へ移動できます。
- **キーワード検索**: メモ本文を部分一致で検索できます（ページネーション対応）。
- **編集・削除**: 各メモを個別に編集・削除できます。
- **URL の自動リンク化**: メモ本文中の `http(s)://` で始まる URL は自動的にリンクへ変換されます。
- **CLI ツール**: `bn.py` でコマンドラインからメモの一覧取得や Markdown 形式での出力ができます。
- タイムゾーンは `Asia/Tokyo` 固定です。

### 構成ファイル

| ファイル | 役割 |
| --- | --- |
| `index.py` | Web アプリ本体（Bottle のルーティング定義） |
| `bn.py` | コマンドライン用ツール |
| `db_setup.py` | データベース（`note.db`）の初期化スクリプト |
| `adapter.wsgi` | WSGI サーバー（Apache mod_wsgi 等）用アダプター |
| `start.sh` | 開発用の起動スクリプト |
| `deploy/bnote.service` | systemd ユニットファイルのサンプル |
| `*.html` | 画面テンプレート（Bottle SimpleTemplate） |
| `static/style.css` | スタイルシート |

## セットアップ

### 前提

- Python 3.11 以上

### 手順

1. リポジトリを取得し、ディレクトリへ移動します。

   ```bash
   cd /home/tf/services/bnote
   ```

2. 仮想環境を作成し、有効化します。

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストールします（`pyproject.toml` に定義されています）。

   ```bash
   pip install bottle==0.12.23 python-dateutil==2.8.2
   ```

   または、pyproject.toml から直接インストールします。

   ```bash
   pip install .
   ```

4. データベースを初期化します。`note.db` が作成され、`notes` テーブルとサンプル行が 1 件追加されます。

   ```bash
   python3 db_setup.py
   ```

   > すでに `note.db` が存在する場合、この手順を実行するとサンプル行が追加されます。既存 DB をそのまま使う場合は実行不要です。

## サービスの起動方法

### 開発用（簡易起動）

`index.py` を直接実行すると、Bottle の開発サーバーが `localhost:8080` で起動します。

```bash
source .venv/bin/activate
python3 index.py
```

ブラウザで <http://localhost:8080/> を開きます。

`start.sh` を使うとバックグラウンドで起動します。

```bash
./start.sh
```

### 本番用（systemd）

`deploy/bnote.service` をひな形として利用します。`<USER>` と `<PROJECT_ROOT>` を環境に合わせて書き換えてください。

```bash
sudo cp deploy/bnote.service /etc/systemd/system/bnote.service
sudo nano /etc/systemd/system/bnote.service   # <USER>, <PROJECT_ROOT> を編集
sudo systemctl daemon-reload
sudo systemctl enable --now bnote.service
```

状態の確認:

```bash
systemctl status bnote.service
```

### 本番用（WSGI）

Apache の mod_wsgi などから配信する場合は `adapter.wsgi` を利用します。この場合、アプリはリバースプロキシ配下の `/bnote` パスで動作する前提になります（`index.py` の `base_url` 参照）。

## サービスの停止方法

### 開発用

- フォアグラウンドで起動した場合: `Ctrl + C` で停止します。
- `start.sh` などでバックグラウンド起動した場合: プロセスを終了します。

  ```bash
  pkill -f "python3 index.py"
  ```

### systemd

```bash
sudo systemctl stop bnote.service
```

自動起動も無効化する場合:

```bash
sudo systemctl disable bnote.service
```

## CLI ツール（bn.py）

```bash
# 全件、または日付・タイプで絞り込んで一覧表示（CSV 風出力）
python3 bn.py list
python3 bn.py list -d 2026-09-01
python3 bn.py list -t action

# 指定日（省略時は当日）のメモを Markdown 形式で出力
python3 bn.py md
python3 bn.py md -d 2026-09-01
```

## 主なエンドポイント

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/` , `/new` | 新規メモ入力画面 |
| POST | `/add` | メモの新規登録・更新 |
| GET | `/list` | 当日のメモ一覧 |
| GET | `/list/<YYYY-MM-DD>` | 指定日のメモ一覧 |
| GET | `/list-all?page=N` | 全メモ一覧（ページネーション） |
| GET | `/search?q=<keyword>&page=N` | キーワード検索 |
| GET | `/edit/<id>` | メモの編集画面 |
| GET | `/delete/<id>` | メモの削除 |
