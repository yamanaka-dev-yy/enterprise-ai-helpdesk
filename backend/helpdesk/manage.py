"""Local interactive account management. Does not place passwords in shell history."""
import argparse
import getpass
from uuid import uuid4

from .auth import password_hash
from .config import Settings
from .db import audit, connect, initialize


def main():
    parser = argparse.ArgumentParser(description="通常ログイン用のアカウントをローカルで作成")
    parser.add_argument("--role", choices=["admin", "employee"], required=True)
    args = parser.parse_args()
    settings = Settings()
    initialize(settings.database)
    email = input("メールアドレス: ").strip().lower()
    if "@" not in email or len(email) > 200:
        raise SystemExit("メールアドレスを確認してください。")
    password = getpass.getpass("パスワード（12文字以上・入力は非表示）: ")
    if len(password) < 12 or len(password) > 128:
        raise SystemExit("パスワードは12〜128文字で指定してください。")
    if password != getpass.getpass("パスワードを再入力: "):
        raise SystemExit("パスワードが一致しません。")
    with connect(settings.database) as db:
        if db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            raise SystemExit("既に登録されています。既存アカウントは変更しません。")
        db.execute("INSERT INTO users VALUES (?,?,?,?)", (str(uuid4()), email, password_hash(password), args.role))
    audit(settings.database, "account_created")
    print("アカウントを作成しました。ログイン画面から利用できます。")


if __name__ == "__main__":
    main()
