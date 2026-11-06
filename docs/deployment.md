# 無料枠での公開準備

確認日: 2026-11-05．現在はローカル実装で，公開URLはまだありません．

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

**公開用LiteLLM ProxyはこのRender構成には含めない．** 無料サービスを複数常時起動すると共有無料稼働時間を消費するため，単一の無料Web ServiceにProxyまで収容する案か，別の無料枠ゲートウェイを，キー取得後に実測・検証して選ぶ．それまでは本文抜粋モードの公開であり，原案の「LiteLLM経由でモデル利用」のクラウド実証は未完了．

無料プロバイダーを使う場合も有料枠は有効にせず，無料のモデルと制限を公式画面で確認する．アプリ内上限は補助．プロバイダー上限・障害時は原文抜粋になる．

## 公式の確認先

- [Render無料枠](https://render.com/docs/free): 月750時間を共有．15分間アクセスがないと休止．無料サービスは永続ディスク非対応．
- [RenderでのFastAPI](https://render.com/docs/deploy-fastapi)
- [Gemini API料金](https://ai.google.dev/gemini-api/docs/pricing): 無料対象モデル・上限・データ取扱いを確認．
- [LiteLLM Proxy](https://docs.litellm.ai/docs/simple_proxy): 接続と構成の確認．

無料枠の条件・新規登録条件は変更される可能性があるため，実際の登録画面でも確認する．
