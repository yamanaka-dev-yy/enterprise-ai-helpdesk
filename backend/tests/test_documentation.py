import json
import shutil
from pathlib import Path

import pytest

from scripts import sync_docs


def test_prose_uses_requested_punctuation_but_preserves_code():
    text = '文書、説明。\n`入力、原文。`\n```python\nprint("入力、原文。")\n```\n文書、説明。\n'
    actual = sync_docs.normalize_prose(text)
    assert actual.startswith('文書，説明．\n`入力、原文。`')
    assert 'print("入力、原文。")' in actual
    assert actual.endswith('文書，説明．\n')


def test_section_replacement_preserves_handwritten_content():
    original = f'説明を保持．\n{sync_docs.START}\n古い内容\n{sync_docs.END}\n末尾も保持．\n'
    actual = sync_docs.replace_section(original, '新しい内容')
    assert actual.startswith('説明を保持．\n')
    assert actual.endswith('末尾も保持．\n')
    assert '古い内容' not in actual
    assert sync_docs.replace_section(actual, '新しい内容') == actual


def test_unbalanced_generation_markers_are_rejected():
    with pytest.raises(ValueError):
        sync_docs.replace_section(sync_docs.START, '内容')


def test_api_reference_extracts_real_authorization():
    rows = {(method, path): (access, csrf) for path, method, _, access, csrf in sync_docs.endpoints(sync_docs.ROOT)}
    assert rows['GET', '/api/health'] == ('認証不要', '不要')
    assert rows['POST', '/api/chat'] == ('ログイン必須', '必要')
    assert rows['POST', '/api/documents'] == ('通常管理者のみ', '必要')
    assert rows['GET', '/api/admin/overview'] == ('管理者のみ', '不要')


def test_generation_does_not_read_environment(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'DO-NOT-PUBLISH-PRIVATE-KEY')
    monkeypatch.setenv('DATABASE_PATH', '/private/DO-NOT-PUBLISH-DATABASE')
    result = sync_docs.reference(sync_docs.ROOT)
    assert 'DO-NOT-PUBLISH' not in result
    assert '| `LLM_API_KEY` | 未設定 |' in result


def test_generation_is_deterministic_and_detects_source_changes(tmp_path):
    root = sync_docs.ROOT
    for path in sync_docs.source_files(root):
        dest = tmp_path / path.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    for relative in ('README.md', 'AGENTS.md', 'docs/specification.md'):
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, dest)
    assert sync_docs.synchronize(tmp_path)
    assert not sync_docs.synchronize(tmp_path, check=True)
    source = tmp_path / 'backend/helpdesk/main.py'
    source.write_text(source.read_text().replace('def health():', 'def health():\n        # Test source change'))
    assert sync_docs.synchronize(tmp_path, check=True)
    assert sync_docs.synchronize(tmp_path)
    assert not sync_docs.synchronize(tmp_path, check=True)


def test_readme_does_not_name_application_target_companies():
    readme = (Path(__file__).resolve().parents[2] / 'README.md').read_text()
    assert '日本光電' not in readme
    assert 'Nihon Kohden' not in readme


def test_data_reference_tracks_seed_and_case_changes(tmp_path):
    for relative in ('backend/helpdesk/seed.py', 'docs/evaluation-cases.json'):
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sync_docs.ROOT / relative, dest)
    original = sync_docs.test_data_reference(tmp_path)
    seed = tmp_path / 'backend/helpdesk/seed.py'
    seed.write_text(seed.read_text().replace('合計20MB', '合計25MB'))
    cases_path = tmp_path / 'docs/evaluation-cases.json'
    cases = json.loads(cases_path.read_text())
    cases[0]['expected_points'].append('変更追跡の確認用の要点')
    cases_path.write_text(json.dumps(cases, ensure_ascii=False))
    updated = sync_docs.test_data_reference(tmp_path)
    assert original != updated
    assert '合計25MB' in updated
    assert '変更追跡の確認用の要点' in updated


def test_evaluation_cases_have_valid_evidence_and_review_criteria():
    from helpdesk.seed import DOCUMENTS

    documents = {doc['id']: doc for doc in DOCUMENTS}
    cases = json.loads((sync_docs.ROOT / 'docs/evaluation-cases.json').read_text())
    assert len({case['id'] for case in cases}) == len(cases)
    for case in cases:
        assert case['scenario'] and case['expected_points'] and case['forbidden']
        if case['status'] == 'answered':
            doc = documents[case['document']]
            assert doc['role'] == 'employee' or case['role'] == 'admin'
            assert case['expected_sections']
            for section in case['expected_sections']:
                assert f'# {section}\n' in doc['text']
        else:
            assert not case.get('document') and not case['expected_sections']


def test_sync_includes_contribution_guide_and_pr_template(tmp_path):
    for path in sync_docs.source_files(sync_docs.ROOT):
        dest = tmp_path / path.relative_to(sync_docs.ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    for relative in ('README.md', 'AGENTS.md', 'docs/specification.md'):
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sync_docs.ROOT / relative, dest)
    for relative in ('CONTRIBUTING.md', '.github/PULL_REQUEST_TEMPLATE.md'):
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('説明、文書。\n`原文、保持。`\n')
    assert sync_docs.synchronize(tmp_path)
    for relative in ('CONTRIBUTING.md', '.github/PULL_REQUEST_TEMPLATE.md'):
        assert (tmp_path / relative).read_text() == '説明，文書．\n`原文、保持。`\n'
    assert not sync_docs.synchronize(tmp_path, check=True)
