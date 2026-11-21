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
| `backup.py` | データベースのバックアップスクリプト（世代管理付き） |
| `adapter.wsgi` | WSGI サーバー（Apache mod_wsgi 等）用アダプター |
| `start.sh` | 開発用の起動スクリプト |
| `deploy/bnote.service` | systemd ユニットファイル（専用ユーザー `bnote` で動かすシステムサービス用。推奨） |
| `deploy/bnote.user.service` | systemd ユニットファイルのサンプル（自分のアカウントで動かすユーザーサービス用） |
| `deploy/bnote-backup.service`, `deploy/bnote-backup.timer` | 毎日バックアップを取る systemd の service と timer |
| `*.html` | 画面テンプレート（Bottle SimpleTemplate） |
| `static/style.css` | スタイルシート |

## セットアップ

### 前提

- Python 3.11 以上

### 手順

1. リポジトリを取得し、ディレクトリへ移動します。

   ```bash
   cd ~/services/bnote
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

4. データベースを初期化します。スクリプトと同じディレクトリに `note.db` が作成され、`notes` テーブルとサンプル行が 1 件追加されます。`note.db` のパーミッションは所有者のみ読み書き可（`600`）に設定されます。

   ```bash
   python3 db_setup.py
   ```

   > すでに `note.db` が存在する場合、この手順を実行するとサンプル行が追加されます。既存 DB をそのまま使う場合は実行不要です。その場合も `chmod 600 note.db` でパーミッションを絞ってください。

### 環境変数

| 変数 | 既定値 | 説明 |
| --- | --- | --- |
| `BNOTE_DB` | `index.py` と同じディレクトリの `note.db` | データベースファイルのパス。`index.py`・`bn.py`・`db_setup.py` のすべてが参照します。専用ユーザーで動かす構成では `/var/lib/bnote/note.db` を指定します。 |

## セキュリティ上の前提

### 認証はリバースプロキシで行う

bnote 自体はユーザー認証の機能を持ちません。**インターネットなど信頼できないネットワークに公開する場合は、必ずリバースプロキシ（nginx、Apache など）を前段に置き、そこで認証（Basic 認証、OAuth2 Proxy、クライアント証明書など）を行ってください。** 認証なしで公開すると、誰でもメモを閲覧・改ざん・削除できる状態になります。

- アプリ（Bottle 開発サーバー）は `localhost:8080` で待ち受けます。外部から直接アクセスできないようにし、必ずプロキシを経由させてください。
- プロキシと利用者の間の通信は HTTPS にしてください。

### プロキシに必要な設定

POST リクエスト（`/add`、`/delete/<id>`）では CSRF 対策として、`Origin` ヘッダー（ない場合は `Referer`）のホストがリクエスト先のホストと一致するかを検証し、一致しなければ `403` を返します。アプリは `X-Forwarded-Host` または `Host` ヘッダーからリクエスト先ホストを判定するので、プロキシでは元のホスト名を渡してください。

nginx の例:

```nginx
location / {
    auth_basic           "bnote";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass           http://127.0.0.1:8080;
    proxy_set_header     Host $host;
}
```

Apache（mod_proxy）は `X-Forwarded-Host` を自動で付与するので、追加の設定は不要です。

### アプリ側で行っている対策

- CSRF 対策: 上記の `Origin` / `Referer` 検証を行い、削除は POST のみ受け付けます。
- セキュリティヘッダー: エラー応答（403/404/405/500 など）を含むすべての応答に、以下を付与します。WSGI ミドルウェア（`index.app`）で付けているため、起動時や `adapter.wsgi` では `bottle.default_app()` ではなく `index.app` を使ってください。
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy: default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'`
  - `Referrer-Policy: same-origin`
  - `X-Content-Type-Options: nosniff`
  - `Strict-Transport-Security: max-age=31536000`（HSTS。HTTPS 接続時のみブラウザが有効にします。サブドメインも HTTPS 専用にしてよい場合は、プロキシ側で `includeSubDomains` を付けてください）
- メモ本文中の自動リンクには `rel="noreferrer noopener"` を付与し、検索語などを含む URL がリンク先に送られないようにしています。
- 入力値を検証し、不正な値には `400`、存在しない日付やメモには `404` を返します。

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

どちらの方法でも、ユニットは `.venv/bin/python` で `index.py` を直接起動します（`Type=simple`）。`start.sh` のようにバックグラウンド（`&`）で起動して終了するスクリプトをユニットから呼ぶと、プロセスが systemd の管理から外れてしまい、異常終了しても自動再起動されず、`systemctl stop` でも止まらなくなるので使わないでください。

#### 専用ユーザーで動かす場合（推奨）

ログインできない専用のシステムユーザー `bnote` でシステムサービスとして動かします。自分のアカウント（sudo や docker を使えるユーザー）で動かすと、アプリが乗っ取られたときにその権限まで奪われるため、本番ではこの方法を使ってください。

構成は次のとおりです。

| 用途 | 場所 | 所有者・権限 |
| --- | --- | --- |
| コード・venv | `/opt/bnote` | `root:root`（サービスからは読み取り専用） |
| データベース | `/var/lib/bnote/note.db` | `bnote:bnote`（ディレクトリ `700`、ファイル `600`） |
| ユニット | `/etc/systemd/system/bnote.service` | `root:root` |

DB の場所は環境変数 `BNOTE_DB` でユニットから指定します。`deploy/bnote.service` には、書き込みを `/var/lib/bnote` だけに限る・`/home` を見えなくする・localhost 以外との通信を禁止する、などのサンドボックス設定（プロセスの権限を絞る systemd の機能）が入っています。

##### 新規インストール

```bash
# 1. Create the dedicated user (no login, no home directory)
sudo useradd --system --user-group --no-create-home \
  --home-dir /nonexistent --shell /usr/sbin/nologin bnote

# 2. Deploy the code as root-owned, read-only files
sudo rsync -a --delete --chown=root:root \
  --exclude .git --exclude .venv --exclude note.db --exclude '__pycache__' --exclude .ruff_cache --exclude '*.swp' \
  ./ /opt/bnote/
sudo python3 -m venv /opt/bnote/.venv
sudo /opt/bnote/.venv/bin/pip install bottle==0.12.23 python-dateutil==2.8.2
sudo /opt/bnote/.venv/bin/python -m compileall -q /opt/bnote

# 3. Create the database directory and initialize the database
sudo install -d -o bnote -g bnote -m 700 /var/lib/bnote
sudo -u bnote BNOTE_DB=/var/lib/bnote/note.db /opt/bnote/.venv/bin/python /opt/bnote/db_setup.py

# 4. Install and start the unit
sudo cp deploy/bnote.service /etc/systemd/system/bnote.service
sudo systemctl daemon-reload
sudo systemctl enable --now bnote.service
```

- `/opt/bnote` はサービスから書き込めないので、`compileall` で `.pyc`（Python のキャッシュ）を事前に作っておきます。省略しても動作はしますが、起動のたびにコンパイルが行われます。
- `/var/lib/bnote` はユニットの `StateDirectory=bnote` によって、起動のたびに所有者 `bnote`・権限 `700` に保たれます。

##### ユーザーサービスからの移行

すでに `deploy/bnote.user.service` で動かしている場合は、上の手順 1・2 を行ってから、手順 3 の DB 初期化の代わりに既存の DB を移します。

```bash
# Stop the old user service (port 8080 must be free)
systemctl --user disable --now bnote.service

# Back up the database and check that no -journal / -wal files are left
cp -p note.db ~/note.db.bak-$(date +%Y%m%d)
ls note.db*

# Move the database to the new location
sudo install -d -o bnote -g bnote -m 700 /var/lib/bnote
sudo install -o bnote -g bnote -m 600 note.db /var/lib/bnote/note.db
```

続けて手順 4 でユニットをインストールして起動し、問題なく動くことを確認したら古いユニットを削除します。

```bash
rm ~/.config/systemd/user/bnote.service
systemctl --user daemon-reload
```

- 他にユーザーサービスがなければ `sudo loginctl disable-linger $USER` で linger（ログアウト中もユーザーサービスを動かし続ける設定）を無効にできます。他のユーザーサービスが動いている場合は無効にしないでください。
- プロジェクトディレクトリに残った古い `note.db` は、しばらく運用して問題がないことを確かめてから削除してください。

元に戻す場合は、`sudo systemctl disable --now bnote.service` で止めてから、古い `note.db` とユーザーユニットを元に戻して `systemctl --user enable --now bnote.service` を実行します。

##### 動作確認

```bash
systemctl status bnote.service
ps -o user,pid,args -C python               # The process must run as bnote
ss -ltnp | grep 8080                        # Listening on 127.0.0.1:8080
journalctl -u bnote -f                      # Follow the log while using the app
systemd-analyze security bnote.service      # Sandbox exposure score (for reference)
```

##### コードの更新

開発用のディレクトリで変更をコミットしたら、`/opt/bnote` に反映してサービスを再起動します。依存パッケージを変えた場合は `pip install` もやり直してください。

```bash
sudo rsync -a --delete --chown=root:root \
  --exclude .git --exclude .venv --exclude note.db --exclude '__pycache__' --exclude .ruff_cache --exclude '*.swp' \
  ./ /opt/bnote/
sudo /opt/bnote/.venv/bin/python -m compileall -q /opt/bnote
sudo systemctl restart bnote.service
```

`--delete` を付けているので、`/opt/bnote` にある、除外対象以外の余分なファイルは削除されます。`.venv` は除外しているので消えません。

##### 起動に失敗する場合

`journalctl -u bnote` に `SIGSYS`（禁止されたシステムコールの呼び出し）や `Permission denied` が出る場合は、サンドボックス設定が原因です。`/etc/systemd/system/bnote.service` の該当しそうな行（`MemoryDenyWriteExecute`、`SystemCallFilter` など）を 1 行ずつコメントアウトし、`sudo systemctl daemon-reload && sudo systemctl restart bnote` で原因を絞り込んでください。

#### ユーザー権限で動かす場合

root を使わず、自分のアカウントの systemd（`systemctl --user`）で常駐させます。sudo などの権限を持つアカウントで動かすことになるため、本番では上の「専用ユーザーで動かす場合」を推奨します。事前に「セットアップ」の手順に従って `.venv` に依存パッケージをインストールしておきます。`deploy/bnote.user.service` はリポジトリが `~/services/bnote` にある前提で書いてあるので、違う場所に置く場合はパスを書き換えてください（`%h` はホームディレクトリに置き換わります）。

```bash
mkdir -p ~/.config/systemd/user
cp deploy/bnote.user.service ~/.config/systemd/user/bnote.service
systemctl --user daemon-reload
systemctl --user enable --now bnote.service
sudo loginctl enable-linger $USER   # ログアウト中や OS 起動直後も動かすために必要（初回のみ）
```

状態の確認は `systemctl --user status bnote.service`、ログの確認は `journalctl --user -u bnote` で行います。

- `[Install]` には `WantedBy=default.target` を指定します。`multi-user.target` はユーザー用の systemd には存在しないので、指定しても自動起動されません。
- サンドボックス設定（`ProtectSystem` など）は、unprivileged user namespace（一般ユーザーが使える名前空間機能）が有効でないと動きません。名前空間関係のエラーで起動に失敗する場合は、ユニット内のこのブロックを削除してください。`note.db` は `index.py` と同じディレクトリに作られるため、書き込みを許可するディレクトリ（`ReadWritePaths`）はプロジェクトのディレクトリにしています。

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

ユーザー権限で動かしている場合は、以下の `sudo systemctl` を `systemctl --user` に読み替えてください。

```bash
sudo systemctl stop bnote.service
```

自動起動も無効化する場合:

```bash
sudo systemctl disable bnote.service
```

## バックアップ

`backup.py` は SQLite のオンラインバックアップ機能（サービスを止めずに、書き込み途中でも一貫した状態を複製する仕組み）で DB を複製します。複製したファイルに整合性チェック（`PRAGMA integrity_check`）をかけ、問題がなければ `note-YYYYMMDD-HHMMSS.db` という名前で保存し、新しいものから指定した数だけ残して古いものを削除します。元の DB は読み取り専用で開くので、バックアップ処理が DB を変更することはありません。

| 環境変数 | 既定値 | 説明 |
| --- | --- | --- |
| `BNOTE_DB` | `backup.py` と同じディレクトリの `note.db` | バックアップ元の DB |
| `BNOTE_BACKUP_DIR` | DB と同じディレクトリの `backups/` | 保存先ディレクトリ（なければ権限 `700` で作成） |
| `BNOTE_BACKUP_KEEP` | `14` | 残すバックアップの数 |

### systemd timer で毎日取る

専用ユーザー構成では、`deploy/bnote-backup.timer` が毎日 3:30 頃（最大 10 分のランダムな遅れあり）に `deploy/bnote-backup.service` を起動し、`/var/lib/bnote/backups` に 14 世代を残します。処理は `bnote` ユーザーで、ネットワークを使えない状態で動きます。その時刻にマシンが止まっていた場合は、次に起動したときに実行されます（`Persistent=true`）。

```bash
# /opt/bnote must already contain backup.py (see "コードの更新")
sudo cp deploy/bnote-backup.service deploy/bnote-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bnote-backup.timer

# Run a backup right away and check the result
sudo systemctl start bnote-backup.service
journalctl -u bnote-backup -n 20
sudo ls -l /var/lib/bnote/backups
```

次回の実行予定は `systemctl list-timers bnote-backup.timer` で確認できます。時刻や残す数を変えるときは `/etc/systemd/system/` のファイルを編集し、`sudo systemctl daemon-reload` を実行します。

### バックアップから戻す

```bash
sudo systemctl stop bnote.service
sudo -u bnote cp /var/lib/bnote/note.db /var/lib/bnote/note.db.before-restore
sudo -u bnote cp /var/lib/bnote/backups/note-YYYYMMDD-HHMMSS.db /var/lib/bnote/note.db
sudo systemctl start bnote.service
```

### 注意

バックアップは DB と同じディスクに保存されるので、ディスクの故障やサーバーそのものを失った場合には役に立ちません。重要なデータであれば、`/var/lib/bnote/backups` を定期的に別のマシンやストレージへコピーしてください。

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

専用ユーザーで動かしている場合、DB は `bnote` ユーザーしか読み書きできないので、`bnote` ユーザーとして `BNOTE_DB` を指定して実行します。

```bash
sudo -u bnote BNOTE_DB=/var/lib/bnote/note.db /opt/bnote/.venv/bin/python /opt/bnote/bn.py list
```

よく使う場合はエイリアス（コマンドの別名）にしておくと便利です。

```bash
alias bn='sudo -u bnote BNOTE_DB=/var/lib/bnote/note.db /opt/bnote/.venv/bin/python /opt/bnote/bn.py'
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
| POST | `/delete/<id>` | メモの削除 |
