# ソースコードから生成したリファレンス

このファイルは `python3 scripts/sync_docs.py` で自動生成します．手動で編集しないでください．

ソース指紋: `c82d5bdb2f22ef49`

## API一覧

| メソッド | パス | 実装関数 | アクセス制御 | CSRF |
|---|---|---|---|---|
| GET | `/api/admin/overview` | `overview` | 管理者のみ | 不要 |
| POST | `/api/auth/demo` | `demo` | 認証不要 | 不要 |
| POST | `/api/auth/login` | `login` | 認証不要 | 不要 |
| POST | `/api/auth/logout` | `logout` | ログイン必須 | 必要 |
| GET | `/api/auth/me` | `me` | ログイン必須 | 不要 |
| POST | `/api/chat` | `chat` | ログイン必須 | 必要 |
| GET | `/api/config` | `config` | 認証不要 | 不要 |
| GET | `/api/documents` | `documents` | ログイン必須 | 不要 |
| POST | `/api/documents` | `add_document` | 通常管理者のみ | 必要 |
| POST | `/api/documents/pdf` | `add_pdf` | 通常管理者のみ | 必要 |
| DELETE | `/api/documents/{document_id}` | `delete_document` | 通常管理者のみ | 必要 |
| PUT | `/api/documents/{document_id}` | `update_document` | 通常管理者のみ | 必要 |
| GET | `/api/health` | `health` | 認証不要 | 不要 |
| GET | `/api/tickets` | `tickets` | ログイン必須 | 不要 |
| POST | `/api/tickets` | `ticket` | ログイン必須 | 必要 |
| PATCH | `/api/tickets/{ticket_id}` | `update_ticket` | 管理者のみ | 必要 |

アクセス制御は依存関係と管理者確認の呼び出しから抽出しています．詳細なデータ分離条件は実装とテストを参照してください．

## 環境変数

アプリ設定の宣言から取得した既定値です．実行環境の `.env` や秘密情報は読み取りません．

| 変数 | 宣言上の既定値 |
|---|---|
| `ADMIN_EMAIL` | 未設定 |
| `ADMIN_PASSWORD` | 未設定 |
| `AI_DAILY_LIMIT` | `30` |
| `COOKIE_SECURE` | `false` |
| `DATABASE_PATH` | `str(ROOT / 'data/helpdesk.sqlite3')` |
| `EMBEDDING_MODEL` | 未設定 |
| `EMPLOYEE_EMAIL` | 未設定 |
| `EMPLOYEE_PASSWORD` | 未設定 |
| `ENABLE_DEMO` | `true` |
| `INPUT_USD_PER_MILLION` | 未設定 |
| `LLM_API_KEY` | 未設定 |
| `LLM_BASE_URL` | 未設定 |
| `LLM_MODEL` | `helpdesk-model` |
| `OUTPUT_USD_PER_MILLION` | 未設定 |
| `SESSION_AI_LIMIT` | `8` |

## 認証の有効期限

| 定数 | 秒 |
|---|---|
| `DEMO_SECONDS` | 7200 |
| `REMEMBER_SECONDS` | 2592000 |
| `SESSION_SECONDS` | 43200 |

## フロントエンド依存関係

| パッケージ | バージョン |
|---|---|
| `lucide-react` | `1.69.0` |
| `next` | `16.4.5` |
| `react` | `19.3.1` |
| `react-dom` | `19.3.1` |

## バックエンドの固定依存関係

| パッケージ | バージョン |
|---|---|
| `annotated-doc` | `0.0.5` |
| `annotated-types` | `0.8.0` |
| `anyio` | `4.16.0` |
| `certifi` | `2026.10.23` |
| `click` | `8.5.0` |
| `fastapi` | `0.162.0` |
| `h11` | `0.16.0` |
| `httpcore` | `1.0.9` |
| `httptools` | `0.9.0` |
| `httpx` | `0.28.1` |
| `idna` | `3.20` |
| `opentelemetry-api` | `1.45.2` |
| `pydantic` | `2.14.2` |
| `pydantic_core` | `2.50.2` |
| `pypdf` | `6.21.4` |
| `python-dotenv` | `1.2.4` |
| `python-multipart` | `0.0.33` |
| `pyyaml` | `6.0.3` |
| `starlette` | `1.10.0` |
| `typing-inspection` | `0.4.5` |
| `typing_extensions` | `4.16.0` |
| `uvicorn` | `0.54.0` |
| `uvloop` | `0.23.0` |
| `watchfiles` | `1.3.0` |
| `websockets` | `17.4` |

## テスト関数の一覧

パラメーター展開前の関数を列挙します．実際の実行件数や成功結果はCIで確認してください．

| ファイル | テスト関数 |
|---|---|
| `backend/tests/test_auth.py` | `test_requires_login` |
| `backend/tests/test_auth.py` | `test_real_login_cookie_and_logout` |
| `backend/tests/test_auth.py` | `test_persistent_cookie_is_opt_in` |
| `backend/tests/test_auth.py` | `test_password_spaces_are_significant` |
| `backend/tests/test_auth.py` | `test_login_error_does_not_reveal_account_existence` |
| `backend/tests/test_auth.py` | `test_session_rotation` |
| `backend/tests/test_auth.py` | `test_expired_session_is_denied` |
| `backend/tests/test_auth.py` | `test_csrf_and_origin_are_checked` |
| `backend/tests/test_auth.py` | `test_role_cannot_be_injected_in_login_or_question` |
| `backend/tests/test_auth.py` | `test_rate_limit_auth` |
| `backend/tests/test_auth.py` | `test_metadata_has_no_secrets_and_api_is_not_cached` |
| `backend/tests/test_auth.py` | `test_demo_cannot_request_remembered_cookie` |
| `backend/tests/test_boundaries.py` | `test_body_limit_handles_missing_length` |
| `backend/tests/test_boundaries.py` | `test_secure_cookie_and_persistent_expiration` |
| `backend/tests/test_boundaries.py` | `test_embedding_path_still_uses_authorized_candidates` |
| `backend/tests/test_boundaries.py` | `test_invalid_provider_json_falls_back` |
| `backend/tests/test_boundaries.py` | `test_blank_pdf_is_rejected_and_no_document_added` |
| `backend/tests/test_boundaries.py` | `test_demo_can_be_disabled` |
| `backend/tests/test_boundaries.py` | `test_chat_rate_limit` |
| `backend/tests/test_documentation.py` | `test_prose_uses_requested_punctuation_but_preserves_code` |
| `backend/tests/test_documentation.py` | `test_section_replacement_preserves_handwritten_content` |
| `backend/tests/test_documentation.py` | `test_unbalanced_generation_markers_are_rejected` |
| `backend/tests/test_documentation.py` | `test_api_reference_extracts_real_authorization` |
| `backend/tests/test_documentation.py` | `test_generation_does_not_read_environment` |
| `backend/tests/test_documentation.py` | `test_generation_is_deterministic_and_detects_source_changes` |
| `backend/tests/test_documentation.py` | `test_readme_does_not_name_application_target_companies` |
| `backend/tests/test_documentation.py` | `test_sync_includes_contribution_guide_and_pr_template` |
| `backend/tests/test_rag.py` | `test_grounded_extraction_and_sources` |
| `backend/tests/test_rag.py` | `test_no_evidence_is_withheld` |
| `backend/tests/test_rag.py` | `test_access_filter_prevents_leaks` |
| `backend/tests/test_rag.py` | `test_prompt_injection_is_refused` |
| `backend/tests/test_rag.py` | `test_proxy_receives_only_authorized_evidence` |
| `backend/tests/test_rag.py` | `test_unrecognized_citation_is_withheld` |
| `backend/tests/test_rag.py` | `test_provider_failure_falls_back_without_leaking_error` |
| `backend/tests/test_rag.py` | `test_zero_budget_never_calls_provider` |
| `backend/tests/test_rag.py` | `test_budget_reservations_are_atomic` |
| `backend/tests/test_rag.py` | `test_audit_logs_do_not_include_question_or_password` |
| `backend/tests/test_rag.py` | `test_input_validation` |
| `backend/tests/test_workflows.py` | `test_demo_tickets_are_isolated_and_deleted_on_logout` |
| `backend/tests/test_workflows.py` | `test_ticket_creation_is_idempotent_and_copies_evidence` |
| `backend/tests/test_workflows.py` | `test_normal_admin_can_manage_normal_ticket_but_not_demo` |
| `backend/tests/test_workflows.py` | `test_demo_admin_cannot_write_shared_manuals` |
| `backend/tests/test_workflows.py` | `test_document_crud_and_search_updates` |
| `backend/tests/test_workflows.py` | `test_invalid_pdf_is_rejected` |
