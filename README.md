# Enterprise AI Helpdesk

架空企業向けの社内ITヘルプデスク．ログインした社員が権限内の資料を検索し，出典を確認できます．回答できない内容は会話と出典を添えた問い合わせに引き継ぎます．生成AIエンジニア応募用のポートフォリオとして開発しています．実在企業のサービス・資料ではありません．

## 実装済み

- Next.js / TypeScriptの業務ツール型画面．ログイン画面から開始．
- FastAPIの通常ログイン，scryptパスワードハッシュ，サーバー側セッション．
- 「ログインしたままにする」: 選択時30日，未選択時ブラウザーセッションCookie＋サーバー有効期限12時間．
- 社員・管理者デモ（2時間）．問い合わせは訪問者ごとに隔離．共有文書は変更不可．
- 検索前の文書ACL，出典の原文展開，根拠不足時の回答保留．
- 文字bigram TF-IDFによる軽量な検索．デフォルトは**検索した本文の抜粋**で，AI生成とは表示しません．
- LiteLLM Proxy互換のOpenAI API接続，出典ID検証，障害・上限到達時の抜粋への切替．
- 任意のEmbedding APIによる再順位付け（既定OFF）．全文意味検索ではなく，TF-IDF候補の再順位付けです．
- 通常管理者によるテキスト/PDF文書登録，編集，閲覧範囲の変更，削除．
- 問い合わせ登録，会話・出典の引き継ぎ，管理者の対応状況変更．
- モデル利用量，設定単価による生成費用の概算，本文を含まない監査ログ．
- Cookie・CSRF・同一オリジン確認，入力制限，試行回数制限，AI利用回数の原子的な予約．
- 自動テスト，CI定義，Docker，無料Render向け構成．

ソースコード: [yamanaka-dev-yy/enterprise-ai-helpdesk](https://github.com/yamanaka-dev-yy/enterprise-ai-helpdesk)

公開デモ: [Enterprise AI Helpdesk](https://enterprise-ai-helpdesk.onrender.com)

2026-11-06，公開HTTPS環境で社員・管理者のデモログイン，資料検索・出典の展開，回答保留，問い合わせ登録，ログアウトを確認しました．**実AIは未接続のため，現在の回答は資料本文の抜粋です．** 通常アカウントは未発行なので，ログイン画面のデモ体験ボタンを使用してください．

無料インスタンスが休止中の場合，初回のアクセスで起動待ちになることがあります．再起動などで追加データやログイン状態が失われる構成です．GitHub Actionsの実行状況はリポジトリのActionsタブで確認できます．

## 起動

Python 3.11，Node.js 22以降を使用．MacではPythonを `python3.11` などに読み替えてください．

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock.txt
cd frontend
npm ci
npm run build
cd ..
PYTHONPATH=backend .venv/bin/uvicorn helpdesk.main:app --host 127.0.0.1 --port 8765 --no-access-log
```

[ローカル画面](http://127.0.0.1:8765)を開いて「社員としてデモ体験」または「管理者としてデモ体験」を選択します．AIキー・通常アカウントがなくても一連の操作を確認できます．

### 通常アカウント

```sh
PYTHONPATH=backend .venv/bin/python -m helpdesk.manage --role admin
PYTHONPATH=backend .venv/bin/python -m helpdesk.manage --role employee
```

対話形式でメールアドレスとパスワードを入力します．パスワードは表示されません．サーバーを再起動してもローカルのDBが残る限り利用できます．環境変数 `ADMIN_EMAIL` / `ADMIN_PASSWORD` 等による初期アカウント作成にも対応します．既存ユーザーのパスワードは自動上書きしません．

### Docker

```sh
docker compose up --build
```

[Docker起動画面](http://127.0.0.1:8000)で確認．ローカルDockerはボリュームに保存し，無料Renderは再起動時にデータが失われるという違いがあります．

### 任意の生成AI接続

`.env.example` を `.env` にコピーし，LiteLLM ProxyのURL・キー・モデルを設定します．プロバイダーの請求設定や有料枠は自動で有効にしません．

ローカルでLiteLLM Proxyも起動する場合:

```sh
docker compose -f compose.yaml -f compose.ai.yaml up --build
```

`.env` に `GEMINI_API_KEY`，プロバイダー接頭辞を含む `GEMINI_MODEL`，十分に長い `LITELLM_MASTER_KEY` が必要です．利用できる無料モデル・レート制限は接続時に確認してください．ProxyはDockerネットワーク内に閉じ，ホストへポート公開しません．

API未設定・障害・上限到達時には本文抜粋へ切り替えます．AI未接続でも使えますが，その状態を「生成AIの動作確認済み」とは説明しません．

## 検証

```sh
.venv/bin/python -m pytest backend/tests -q
.venv/bin/ruff check backend
cd frontend
npm run typecheck
npm run build
```

評価データと制約は [docs/evaluation.md](docs/evaluation.md)．自動テストにはモックのモデル出力を含み，実際のGeminiの品質評価とは区別します．

## 公開と設計

- [無料公開手順](docs/deployment.md)
- [構成・セキュリティ・データの流れ](docs/architecture.md)
- [合意した仕様・実装の範囲](docs/specification.md)
- [ドキュメント自動更新の運用](docs/documentation.md)

無料枠で無制限のAI利用や常時稼働を保証するものではありません．公開デモに実際の個人情報・社内機密を入力しないでください．

<!-- AUTO-GENERATED:START -->
## ソースコードと連動する情報

この節は `python3 scripts/sync_docs.py` で自動生成します．手動で編集しないでください．

| 項目 | 現在のコードから取得した値 |
|---|---|
| API定義 | 16件 |
| バックエンド | FastAPI 0.162.0 / Python 3.11 |
| フロントエンド | Next.js 16.4.5 / React 19.3.1 |
| 通常セッションの上限 | 12時間 |
| ログイン保持の上限 | 30日 |
| デモセッションの上限 | 2時間 |
| ソース指紋 | `57bdbfd9deb3688b` |

API・環境変数・依存関係・テスト関数の一覧は [自動生成リファレンス](docs/reference.md) を参照してください．
<!-- AUTO-GENERATED:END -->
