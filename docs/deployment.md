# 無料枠での公開準備

公開確認日: 2026-11-06．[公開デモ](https://enterprise-ai-helpdesk.onrender.com)をRenderへデプロイし，HTTPS環境でデモログイン・資料検索・出典の展開・回答保留・問い合わせ登録・ログアウトを確認しました．Gemini APIへの直接接続と出典付き生成回答も確認済みです．以下は環境を再作成する場合の手順です．

## まず取得するもの

1. [GitHub](https://github.com/signup)の無料アカウント．確認メール・パスワード・利用規約への同意は本人が行う．
2. [Render](https://dashboard.render.com/register)のアカウント．GitHub連携で対象のリポジトリだけを許可する．
3. 実際のAI生成を使う段階で，Gemini APIなどの無料対象APIキー．秘密情報をチャットやGitHubへ貼らない．

GitHubとRenderだけで，まず本文抜粋モードを公開できる．AI未接続であることは画面に表示する．

## GitHubへの登録

このディレクトリを単独リポジトリにする．他の作業フォルダーやDesktopの応募資料は含めない．

```sh
git init -b main
git add .
git commit -m "Build authenticated helpdesk portfolio MVP"
```

GitHubで空のリポジトリを作成して，表示された接続先を設定・pushする．URLが確定するまでリモート値を推測しない．

`.env`，`data/`，`.venv/`，node_modulesは除外済み．公開前に `git status` とコミット対象を確認する．

## Render

1. Dashboardの「New → Blueprint」またはDocker Web Serviceからリポジトリを選択．
2. Blueprintでは `render.yaml` を利用．**plan: free** が表示されることを確認．
3. 有料ディスク・有料DB・追加有料サービスを選ばない．この構成には不要．
4. 環境変数 `COOKIE_SECURE=true`，`ENABLE_DEMO=true` を確認．
5. Deploy完了後の `https://…onrender.com` を開く．
6. 社員デモ・管理者デモ，回答保留，問い合わせ，ログアウトを実際のHTTPS URLで再確認．

通常ログインを有効にする場合はDashboardの環境変数で `ADMIN_EMAIL` / `ADMIN_PASSWORD` を設定．パスワードは12文字以上．従業員用は `EMPLOYEE_EMAIL` / `EMPLOYEE_PASSWORD`．デモの公開と通常管理者の公開は分けて扱い，通常アカウントの認証情報を応募資料に載せない．

### 保存について

ローカルDBのため，無料Renderの再起動で追加文書・セッション・チケットは消える．初期資料と環境変数で設定したアカウントは起動時に再作成する．起動後に変更したパスワードを永続化する運用には使わない．

## AIの接続

このアプリは `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` でOpenAI互換APIへ接続する．LiteLLM Proxyのローカル再現構成は `compose.ai.yaml` に用意している．

現在の公開デモはGoogleのOpenAI互換APIへ直接接続している．2026-11-06，以下の設定で実モデルによる生成回答と出典表示を確認した．APIキーは利用者本人がRenderへ入力し，リポジトリには含めない．

| 環境変数 | 公開デモの設定 |
|---|---|
| `LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai` |
| `LLM_API_KEY` | Render側のみで管理 |
| `LLM_MODEL` | `gemini-3.1-flash-lite` |
| `AI_DAILY_LIMIT` | `10` |
| `SESSION_AI_LIMIT` | `3` |

**公開用LiteLLM ProxyはこのRender構成には含めない．** 無料環境に収容する方法は今後実測して選ぶ．原案の「LiteLLM経由でモデル利用」のクラウド実証は未完了であり，直接接続と区別する．

無料プロバイダーを使う場合も有料枠は有効にせず，無料のモデルと制限を公式画面で確認する．アプリ内上限は補助．プロバイダー上限・障害時は原文抜粋になる．

応答待ちは `LLM_READ_TIMEOUT_SECONDS` で設定する（既定45秒，5〜60秒に制限）．接続待ちは5秒，送信待ちは10秒で，自動再試行はしない．各処理の待ち時間であり，要求全体の期限ではない．障害時の `failure_code` と安全なサーバーログの読み方は [障害調査と対策](ai-failure-investigation.md) を参照する．

## 公式の確認先

- [Render無料枠](https://render.com/docs/free): 月750時間を共有．15分間アクセスがないと休止．無料サービスは永続ディスク非対応．
- [RenderでのFastAPI](https://render.com/docs/deploy-fastapi)
- [Gemini API料金](https://ai.google.dev/gemini-api/docs/pricing): 無料対象モデル・上限・データ取扱いを確認．
- [LiteLLM Proxy](https://docs.litellm.ai/docs/simple_proxy): 接続と構成の確認．

無料枠の条件・新規登録条件は変更される可能性があるため，実際の登録画面でも確認する．
