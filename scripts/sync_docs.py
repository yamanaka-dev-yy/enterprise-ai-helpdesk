"""Generate factual documentation from source without importing the application．"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- AUTO-GENERATED:START -->"
END = "<!-- AUTO-GENERATED:END -->"
PUNCTUATION = str.maketrans({"、": "，", "。": "．"})


def normalize_prose(text):
    """Normalize Japanese prose while preserving fenced and inline code．"""
    output = []
    fence = None
    for line in text.splitlines(keepends=True):
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            output.append(line)
        elif fence:
            output.append(line)
        else:
            parts = re.split(r"(`+[^`]*`+)", line)
            output.append("".join(part if index % 2 else part.translate(PUNCTUATION)
                                  for index, part in enumerate(parts)))
    return "".join(output)


def tree(root, relative):
    return ast.parse((root / relative).read_text(encoding="utf-8"))


def contains_call(node, name):
    return any(isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
               and item.func.attr == name for item in ast.walk(node))


def endpoints(root):
    rows = []
    for node in ast.walk(tree(root, "backend/helpdesk/main.py")):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):  # noqa: UP038
            continue
        for decorator in node.decorator_list:
            if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr in {"get", "post", "put", "patch", "delete"}
                    and decorator.args and isinstance(decorator.args[0], ast.Constant)):
                continue
            path = decorator.args[0].value
            if not isinstance(path, str) or not path.startswith("/api/"):
                continue
            dependencies = [item.args[0].id if isinstance(item.args[0], ast.Name)
                            else ast.unparse(item.args[0]) for item in ast.walk(node.args)
                            if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
                            and item.func.id == "Depends" and item.args]
            access = "認証不要"
            if dependencies:
                access = "ログイン必須"
            if contains_call(node, "require_admin"):
                writable = any(isinstance(item, ast.keyword) and item.arg == "writable"
                               and isinstance(item.value, ast.Constant) and item.value.value is True
                               for item in ast.walk(node))
                access = "通常管理者のみ" if writable else "管理者のみ"
            rows.append((path, decorator.func.attr.upper(), node.name, access,
                         "必要" if "mutation" in dependencies else "不要"))
    return sorted(rows)


def environment(root):
    rows = {}
    for node in ast.walk(tree(root, "backend/helpdesk/config.py")):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "getenv" and node.args
                and isinstance(node.args[0], ast.Constant)):
            continue
        name = node.args[0].value
        if len(node.args) < 2:
            default = "未設定"
        elif isinstance(node.args[1], ast.Constant):
            value = node.args[1].value
            default = f"`{value}`" if value != "" else "未設定"
        else:
            # Keep symbolic expressions instead of evaluating host paths or secrets．
            default = f"`{ast.unparse(node.args[1])}`"
        rows[name] = default
    return sorted(rows.items())


def constants(root):
    values = {}
    for node in tree(root, "backend/helpdesk/auth.py").body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            # Evaluate only numeric literals and multiplication; never arbitrary Python．
            def number(value):
                if isinstance(value, ast.Constant) and type(value.value) is int:
                    return value.value
                if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mult):
                    return number(value.left) * number(value.right)
                raise ValueError("Not a numeric duration")

            if node.targets[0].id.endswith("_SECONDS"):
                values[node.targets[0].id] = number(node.value)
    return values


def versions(root):
    frontend = json.loads((root / "frontend/package.json").read_text())
    backend = {}
    for line in (root / "requirements.lock.txt").read_text().splitlines():
        if "==" in line and not line.startswith("#"):
            name, version = line.split("==", 1)
            backend[name.lower()] = version
    return frontend, backend


def source_files(root):
    paths = [p for directory in ("backend", "scripts") for p in (root / directory).rglob("*.py")]
    paths += list((root / "frontend/app").rglob("*.tsx"))
    paths += list((root / "frontend/app").rglob("*.css"))
    paths += list((root / ".github/workflows").glob("*.yml"))
    paths += [root / name for name in ("frontend/package.json", "frontend/package-lock.json",
                                      "frontend/tsconfig.json", "frontend/next.config.ts",
                                      "requirements.lock.txt", "requirements-dev.lock.txt",
                                      "requirements.txt", "requirements-dev.txt",
                                      "pyproject.toml", "Dockerfile", "render.yaml", "compose.yaml",
                                      "compose.ai.yaml", "infra/litellm.yaml", ".env.example",
                                      "docs/evaluation-cases.json")]
    return sorted({p for p in paths if p.is_file()}, key=lambda p: p.relative_to(root).as_posix())


def source_digest(root):
    # A source-only commit must also refresh generated references in GitHub Actions．
    digest = hashlib.sha256()
    for path in source_files(root):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def summary(root, link):
    routes = endpoints(root)
    durations = constants(root)
    frontend, backend = versions(root)
    python_version = re.search(r"FROM python:([^\s-]+)", (root / "Dockerfile").read_text()).group(1)
    return ("## ソースコードと連動する情報\n\n"
            "この節は `python3 scripts/sync_docs.py` で自動生成します．手動で編集しないでください．\n\n"
            "| 項目 | 現在のコードから取得した値 |\n|---|---|\n"
            f"| API定義 | {len(routes)}件 |\n"
            f"| バックエンド | FastAPI {backend['fastapi']} / Python {python_version} |\n"
            f"| フロントエンド | Next.js {frontend['dependencies']['next']} / React {frontend['dependencies']['react']} |\n"
            f"| 通常セッションの上限 | {durations['SESSION_SECONDS'] // 3600}時間 |\n"
            f"| ログイン保持の上限 | {durations['REMEMBER_SECONDS'] // 86400}日 |\n"
            f"| デモセッションの上限 | {durations['DEMO_SECONDS'] // 3600}時間 |\n"
            f"| ソース指紋 | `{source_digest(root)}` |\n\n"
            f"API・環境変数・依存関係・テスト関数の一覧は [自動生成リファレンス]({link}) を参照してください．\n")


def reference(root):
    frontend, backend = versions(root)
    text = "# ソースコードから生成したリファレンス\n\n"
    text += "このファイルは `python3 scripts/sync_docs.py` で自動生成します．手動で編集しないでください．\n\n"
    text += f"ソース指紋: `{source_digest(root)}`\n\n"
    text += "## API一覧\n\n| メソッド | パス | 実装関数 | アクセス制御 | CSRF |\n|---|---|---|---|---|\n"
    for path, method, name, access, csrf in endpoints(root):
        text += f"| {method} | `{path}` | `{name}` | {access} | {csrf} |\n"
    text += "\nアクセス制御は依存関係と管理者確認の呼び出しから抽出しています．詳細なデータ分離条件は実装とテストを参照してください．\n"
    text += "\n## 環境変数\n\nアプリ設定の宣言から取得した既定値です．実行環境の `.env` や秘密情報は読み取りません．\n\n| 変数 | 宣言上の既定値 |\n|---|---|\n"
    for name, default in environment(root):
        text += f"| `{name}` | {default} |\n"
    text += "\n## 認証の有効期限\n\n| 定数 | 秒 |\n|---|---|\n"
    for name, seconds in sorted(constants(root).items()):
        text += f"| `{name}` | {seconds} |\n"
    text += "\n## フロントエンド依存関係\n\n| パッケージ | バージョン |\n|---|---|\n"
    for name, version in sorted(frontend["dependencies"].items()):
        text += f"| `{name}` | `{version}` |\n"
    text += "\n## バックエンドの固定依存関係\n\n| パッケージ | バージョン |\n|---|---|\n"
    for name, version in sorted(backend.items()):
        text += f"| `{name}` | `{version}` |\n"
    text += "\n## テスト関数の一覧\n\nパラメーター展開前の関数を列挙します．実際の実行件数や成功結果はCIで確認してください．\n\n| ファイル | テスト関数 |\n|---|---|\n"
    for path in sorted((root / "backend/tests").glob("test_*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):  # noqa: UP038
                text += f"| `{path.relative_to(root).as_posix()}` | `{node.name}` |\n"
    return text


def test_data_reference(root):
    """Read only literal seed data and the fixed evaluation cases．"""
    documents = next(ast.literal_eval(node.value)
                     for node in tree(root, "backend/helpdesk/seed.py").body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "DOCUMENTS"
                             for target in node.targets))
    cases = json.loads((root / "docs/evaluation-cases.json").read_text())
    text = "# テストデータ詳細\n\n"
    text += "このファイルは `python3 scripts/sync_docs.py` で初期資料と評価ケースから自動生成します．手動で編集しないでください．\n\n"
    text += ("すべて架空のデータです．実在企業の規定や実績ではありません．"
             "初期資料は `backend/helpdesk/seed.py`，評価入力は `docs/evaluation-cases.json` が正本です．\n\n"
             "初期資料の変更は新規DBの作成時に反映されます．既存DBでは同じIDの資料を自動上書きしません．"
             "公開環境への反映はマージ・再デプロイとDBの状態に依存します．\n\n"
             "## 判定方法\n\n"
             "自動評価は回答可否と期待する参照文書の有無を確認します．"
             "以下の回答要点・参照節・禁止事項は人手による確認基準であり，自動合格が本文の正確さを保証するものではありません．"
             "言い換えケースも同じ基準で判定し，失敗した場合は隠さず記録します．"
             "実モデルによる検証結果は [評価記録](evaluation.md) で別に管理します．\n\n"
             f"## 検索対象の架空マニュアル（{len(documents)}件）\n\n"
             "社員向け資料は社員・管理者が参照できます．管理者向け資料は管理者だけが参照できます．\n\n")
    for doc in documents:
        text += f"### {doc['title']}\n\nID: `{doc['id']}` ／ 閲覧範囲: `{doc['role']}`\n\n"
        for line in doc['text'].splitlines():
            text += ("#### " + line[2:] + "\n" if line.startswith("# ") else line) + "\n"
        text += "\n"
    text += f"## 評価ケース（{len(cases)}件）\n\n"
    for case in cases:
        text += f"### {case['id']}：{case['category']}\n\n"
        text += f"- 質問：{case['question']}\n- 利用者権限：`{case['role']}`\n"
        text += f"- 利用場面：{case['scenario']}\n"
        text += f"- 期待する回答可否：`{case['status']}`\n"
        text += f"- 期待する参照文書：`{case['document']}`\n" if case.get('document') else "- 期待する参照文書：なし．\n"
        text += "- 確認する参照節：" + (" ／ ".join(case['expected_sections']) or "なし") + "\n"
        if case.get('challenge'):
            text += "- 分類：言い換えの課題ケース．合格済みを意味しません．\n"
        text += "\n期待する回答要点：\n\n" + "".join(f"- {point}\n" for point in case['expected_points'])
        text += "\n答えてはいけない内容・動作：\n\n" + "".join(f"- {point}\n" for point in case['forbidden'])
        text += f"\n判定：{case['review_method']}\n\n"
    return text


def replace_section(text, content):
    if text.count(START) != text.count(END) or text.count(START) > 1:
        raise ValueError("自動生成領域のマーカーが不正です．")
    block = f"{START}\n{content.rstrip()}\n{END}"
    if START in text:
        before, _, rest = text.partition(START)
        _, _, after = rest.partition(END)
        return before + block + after
    return text.rstrip() + "\n\n" + block + "\n"


def planned_changes(root):
    generated = root / "docs/reference.md"
    planned = {generated: reference(root), root / "docs/test-data.md": test_data_reference(root)}
    for relative in ("README.md", "docs/specification.md"):
        path = root / relative
        link = "docs/reference.md" if relative == "README.md" else "reference.md"
        planned[path] = replace_section(path.read_text(), summary(root, link))
    markdown = [*root.glob("*.md"), *(root / "docs").rglob("*.md"),
                *(root / ".github").rglob("*.md")]
    for path in markdown:
        if path.is_file():
            planned[path] = normalize_prose(planned.get(path, path.read_text()))
    planned[generated] = normalize_prose(planned[generated])
    return {path: content for path, content in planned.items() if not path.exists() or path.read_text() != content}


def synchronize(root, check=False):
    changes = planned_changes(root)
    for path, content in changes.items():
        print(("更新が必要: " if check else "更新: ") + path.relative_to(root).as_posix())
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return bool(changes)


def main():
    parser = argparse.ArgumentParser(description="ソースコードからドキュメントを同期します．")
    parser.add_argument("--check", action="store_true", help="変更せずに同期漏れを検出します．")
    args = parser.parse_args()
    changed = synchronize(ROOT, check=args.check)
    raise SystemExit(1 if args.check and changed else 0)


if __name__ == "__main__":
    main()
