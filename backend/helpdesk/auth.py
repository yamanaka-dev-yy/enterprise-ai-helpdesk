import hashlib
import hmac
import secrets
import time
from uuid import uuid4

from fastapi import HTTPException, Request, Response

from .db import connect

COOKIE = "helpdesk_session"
SESSION_SECONDS = 12 * 3600
REMEMBER_SECONDS = 30 * 86400
DEMO_SECONDS = 2 * 3600


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"scrypt${salt}${value}"


DUMMY_HASH = password_hash("not-a-real-account")


def password_valid(password, stored):
    try:
        _, salt, _ = stored.split("$")
        return hmac.compare_digest(password_hash(password, salt), stored)
    except (ValueError, TypeError):
        return False


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def seed_users(settings):
    for email, password, role in [
        (settings.admin_email, settings.admin_password, "admin"),
        (settings.employee_email, settings.employee_password, "employee"),
    ]:
        if not email and not password:
            continue
        if not email or len(password) < 12:
            raise ValueError(f"{role} requires an email and a password of 12 or more characters")
        with connect(settings.database) as db:
            existing = db.execute("SELECT id FROM users WHERE email=?", (email.lower(),)).fetchone()
            if not existing:
                db.execute("INSERT INTO users VALUES (?,?,?,?)",
                           (str(uuid4()), email.lower(), password_hash(password), role))


def current_session(request: Request):
    token = request.cookies.get(COOKIE, "")
    if not token or len(token) > 200:
        raise HTTPException(401, "ログインしてください。")
    with connect(request.app.state.settings.database) as db:
        row = db.execute("SELECT * FROM sessions WHERE token_hash=? AND expires>?",
                         (digest(token), time.time())).fetchone()
    if not row:
        raise HTTPException(401, "ログインの有効期限が切れました。再度ログインしてください。")
    return dict(row)


def check_csrf(request, session):
    if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), session["csrf"]):
        raise HTTPException(403, "操作を確認できませんでした。画面を再読み込みしてください。")


def require_admin(session, writable=False):
    if session["role"] != "admin":
        raise HTTPException(403, "管理者権限が必要です。")
    if writable and session["is_demo"]:
        raise HTTPException(403, "管理者デモでは共有データを変更できません。")


def owner(session):
    return f"demo:{session['token_hash']}" if session["is_demo"] else f"user:{session['user_id']}"


def session_public(session):
    return {"role": session["role"], "is_demo": bool(session["is_demo"]),
            "csrf_token": session["csrf"], "expires": session["expires"]}


def create_session(request: Request, response: Response, role, user_id=None, demo=False, remember=False):
    settings = request.app.state.settings
    old_token = request.cookies.get(COOKIE)
    token = secrets.token_urlsafe(32)
    ttl = DEMO_SECONDS if demo else REMEMBER_SECONDS if remember else SESSION_SECONDS
    now = time.time()
    session = {"token_hash": digest(token), "user_id": user_id, "role": role,
               "is_demo": int(demo), "csrf": secrets.token_urlsafe(32),
               "expires": now + ttl, "created": now}
    with connect(settings.database) as db:
        if old_token:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (digest(old_token),))
        db.execute("INSERT INTO sessions VALUES (:token_hash,:user_id,:role,:is_demo,:csrf,:expires,:created)", session)
    response.set_cookie(COOKIE, token, httponly=True, secure=settings.secure_cookie, samesite="lax",
                        max_age=ttl if remember and not demo else None, path="/")
    return session
