# Enterprise AI Helpdesk

- 架空企業の応募用ポートフォリオ。実在企業の資料・コード・改善実績は使わない。
- 本物のAI生成と、根拠を抜粋するモードを画面とREADMEで区別する。
- 認可は必ずAPI側で実施。クライアントから渡されたroleを信用しない。
- デモは訪問者ごとのセッション。共有資料の変更を許可しない。
- 秘密情報、パスワード、セッショントークン、質問本文を監査ログに記録しない。
- 検証: `.venv/bin/python -m pytest backend/tests`、`.venv/bin/ruff check backend`、`cd frontend && npm run typecheck && npm run build`。
- 無料枠を超える有料サービスの作成や課金設定は行わない。
