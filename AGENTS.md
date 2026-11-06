# Enterprise AI Helpdesk

- 架空企業の応募用ポートフォリオ．実在企業の資料・コード・改善実績は使わない．
- 本物のAI生成と，根拠を抜粋するモードを画面とREADMEで区別する．
- 認可は必ずAPI側で実施．クライアントから渡されたroleを信用しない．
- デモは訪問者ごとのセッション．共有資料の変更を許可しない．
- 秘密情報，パスワード，セッショントークン，質問本文を監査ログに記録しない．
- 検証: `.venv/bin/python -m pytest backend/tests`，`.venv/bin/ruff check backend`，`cd frontend && npm run typecheck && npm run build`．
- 無料枠を超える有料サービスの作成や課金設定は行わない．

## ドキュメント運用

- ドキュメントの日本語の読点は「，」，句点は「．」を使う．コードブロックやインラインコードの内容は変更しない．
- READMEに応募先などの実在企業名を記載しない．
- ソースコードの変更後は `python3 scripts/sync_docs.py` を実行する．生成領域と `docs/reference.md` は手動で編集しない．
- 設計理由・制約・未検証事項に影響する変更では，該当する説明文も更新する．自動生成だけで説明文の整合性を保証したと扱わない．
- 検証に `python3 scripts/sync_docs.py --check` と `.venv/bin/ruff check scripts` を含める．
