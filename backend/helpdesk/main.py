import hashlib
import io
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pypdf import PdfReader

from . import auth
from .config import ROOT, Settings
from .db import accessible_documents, audit, connect, consume_limit, decode_sources, initialize, prune
from .middleware import BodyLimitMiddleware
from .rag import answer_question, question_allowed, save_answer


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    email: str = Field(min_length=3, max_length=200, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=1, max_length=128)
    remember: bool = False

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value):
        return value.strip() if isinstance(value, str) else value


class Demo(StrictModel):
    role: Literal["employee", "admin"]


class Question(StrictModel):
    question: str = Field(min_length=3, max_length=1000)


class NewTicket(StrictModel):
    answer_id: str = Field(min_length=1, max_length=50)


class TicketUpdate(StrictModel):
    status: Literal["open", "in_progress", "closed"]


class Document(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=20, max_length=40000)
    role: Literal["employee", "admin"] = "employee"


def create_app(settings=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        initialize(settings.database)
        auth.seed_users(settings)
        prune(settings.database)
        yield

    app = FastAPI(title="Enterprise AI Helpdesk", version="0.1.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings

    @app.middleware("http")
    async def security(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            # Same-origin only: no permissive CORS. Reject foreign/null Origin explicitly.
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme not in ("http", "https") or parsed.netloc != request.headers.get("host"):
                    return JSONResponse({"detail": "別のサイトからの操作は許可されていません。"}, status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "別のサイトからの操作は許可されていません。"}, status_code=403)
            length = request.headers.get("content-length", "0")
            try:
                too_large = int(length) > 2_200_000
            except ValueError:
                too_large = True
            if too_large:
                return JSONResponse({"detail": "ファイルまたは入力が大きすぎます。"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if settings.secure_cookie:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    def mutation(request: Request, session=Depends(auth.current_session)):
        auth.check_csrf(request, session)
        return session

    def auth_rate_limit(request):
        # The direct peer is used; arbitrary X-Forwarded-For headers are not trusted.
        peer = request.client.host if request.client else "unknown"
        key = hashlib.sha256(peer.encode()).hexdigest()
        if not consume_limit(settings.database, "auth", key, 30, seconds=300):
            raise HTTPException(429, "試行回数が多すぎます。5分ほど待ってお試しください。", headers={"Retry-After": "300"})

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/config")
    def config():
        with connect(settings.database) as db:
            has_users = db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None
        return {"demo_enabled": settings.demo, "normal_login_enabled": has_users,
                "generation_enabled": bool(settings.llm_url and settings.llm_key),
                "retrieval": "tfidf+embedding-rerank" if settings.embedding_model else "char-bigram-tfidf",
                "version": "0.1.0", "remember_days": 30}

    @app.post("/api/auth/login")
    def login(body: Login, request: Request, response: Response):
        auth_rate_limit(request)
        with connect(settings.database) as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (body.email.lower(),)).fetchone()
        valid = auth.password_valid(body.password, user["password_hash"] if user else auth.DUMMY_HASH)
        if not valid or not user:
            audit(settings.database, "login_failed")
            raise HTTPException(401, "メールアドレスまたはパスワードが正しくありません。")
        prune(settings.database)
        session = auth.create_session(request, response, user["role"], user["id"], remember=body.remember)
        audit(settings.database, "login", session)
        return auth.session_public(session)

    @app.post("/api/auth/demo")
    def demo(body: Demo, request: Request, response: Response):
        if not settings.demo:
            raise HTTPException(404, "デモ体験は現在無効です。")
        auth_rate_limit(request)
        prune(settings.database)
        session = auth.create_session(request, response, body.role, demo=True)
        audit(settings.database, "demo_login", session)
        return auth.session_public(session)

    @app.get("/api/auth/me")
    def me(session=Depends(auth.current_session)):
        return auth.session_public(session)

    @app.post("/api/auth/logout")
    def logout(response: Response, session=Depends(mutation)):
        with connect(settings.database) as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (session["token_hash"],))
            if session["is_demo"]:
                session_owner = auth.owner(session)
                db.execute("DELETE FROM answers WHERE owner=?", (session_owner,))
                db.execute("DELETE FROM tickets WHERE owner=?", (session_owner,))
        response.delete_cookie(auth.COOKIE, path="/", secure=settings.secure_cookie, httponly=True, samesite="lax")
        audit(settings.database, "logout", session)
        return {"ok": True}

    @app.post("/api/chat")
    def chat(body: Question, session=Depends(mutation)):
        if not question_allowed(settings, session):
            raise HTTPException(429, "質問回数が多すぎます。1分ほど待ってお試しください。", headers={"Retry-After": "60"})
        result = answer_question(settings, session, body.question)
        result = save_answer(settings, auth.owner(session), body.question, result)
        audit(settings.database, f"question_{result['status']}", session)
        return result

    @app.get("/api/documents")
    def documents(session=Depends(auth.current_session)):
        return [{k: d[k] for k in ("id", "title", "text", "role", "updated", "seeded")}
                for d in accessible_documents(settings.database, session["role"])]

    @app.post("/api/documents", status_code=201)
    def add_document(body: Document, session=Depends(mutation)):
        auth.require_admin(session, writable=True)
        return write_document(body, session)

    def write_document(body, session, document_id=None):
        document_id = document_id or str(uuid4())
        with connect(settings.database) as db:
            if db.execute("SELECT count(*) FROM documents").fetchone()[0] >= 24:
                raise HTTPException(409, "このポートフォリオの登録上限は24文書です。")
            db.execute("INSERT INTO documents (id,title,text,role,updated) VALUES (?,?,?,?,?)",
                       (document_id, body.title, body.text, body.role, time.time()))
        audit(settings.database, "document_created", session)
        return {"id": document_id}

    @app.post("/api/documents/pdf", status_code=201)
    def add_pdf(file: UploadFile, session=Depends(mutation)):
        auth.require_admin(session, writable=True)
        raw = file.file.read(2_000_001)
        if len(raw) > 2_000_000:
            raise HTTPException(413, "PDFは2MB以下にしてください。")
        if not raw.startswith(b"%PDF-"):
            raise HTTPException(422, "PDFファイルを選択してください。")
        try:
            pdf = PdfReader(io.BytesIO(raw))
            if pdf.is_encrypted or len(pdf.pages) > 30:
                raise ValueError("Unsupported PDF")
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as exc:
            raise HTTPException(422, "PDFを読み込めません。暗号化なし・30ページ以下のPDFを指定してください。") from exc
        if len(text.strip()) < 20 or len(text) > 40000:
            raise HTTPException(422, "20〜40,000文字のテキストを含むPDFを指定してください。画像PDFのOCRは未対応です。")
        title = Path(file.filename or "マニュアル.pdf").stem[:100]
        # Admin-only default; publish to employees deliberately through the edit screen.
        return write_document(Document(title=title, text=text, role="admin"), session)

    @app.put("/api/documents/{document_id}")
    def update_document(document_id: str, body: Document, session=Depends(mutation)):
        auth.require_admin(session, writable=True)
        with connect(settings.database) as db:
            changed = db.execute("UPDATE documents SET title=?,text=?,role=?,updated=? WHERE id=?",
                                 (body.title, body.text, body.role, time.time(), document_id)).rowcount
        if not changed:
            raise HTTPException(404, "文書が見つかりません。")
        audit(settings.database, "document_updated", session)
        return {"ok": True}

    @app.delete("/api/documents/{document_id}")
    def delete_document(document_id: str, session=Depends(mutation)):
        auth.require_admin(session, writable=True)
        with connect(settings.database) as db:
            changed = db.execute("DELETE FROM documents WHERE id=?", (document_id,)).rowcount
        if not changed:
            raise HTTPException(404, "文書が見つかりません。")
        audit(settings.database, "document_deleted", session)
        return {"ok": True}

    @app.post("/api/tickets", status_code=201)
    def ticket(body: NewTicket, session=Depends(mutation)):
        session_owner = auth.owner(session)
        with connect(settings.database) as db:
            db.execute("BEGIN IMMEDIATE")
            result = db.execute("SELECT * FROM answers WHERE id=? AND owner=?", (body.answer_id, session_owner)).fetchone()
            if not result:
                raise HTTPException(404, "引き継ぐ回答が見つかりません。")
            if db.execute("SELECT count(*) FROM tickets WHERE owner=?", (session_owner,)).fetchone()[0] >= 20:
                raise HTTPException(409, "問い合わせの上限は20件です。")
            existing = db.execute("SELECT * FROM tickets WHERE answer_id=? AND owner=?", (body.answer_id, session_owner)).fetchone()
            if existing:
                return decode_sources(existing)
            ticket_id = str(uuid4())
            db.execute("INSERT INTO tickets(id,owner,answer_id,question,answer,sources,created) VALUES (?,?,?,?,?,?,?)",
                       (ticket_id, session_owner, body.answer_id, result["question"], result["answer"], result["sources"], time.time()))
            row = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        audit(settings.database, "ticket_created", session)
        return decode_sources(row)

    @app.get("/api/tickets")
    def tickets(session=Depends(auth.current_session)):
        with connect(settings.database) as db:
            # Demo admins see only their own sandbox; real admins see non-demo tickets.
            if session["role"] == "admin" and not session["is_demo"]:
                rows = db.execute("SELECT * FROM tickets WHERE owner LIKE 'user:%' ORDER BY created DESC").fetchall()
            else:
                rows = db.execute("SELECT * FROM tickets WHERE owner=? ORDER BY created DESC", (auth.owner(session),)).fetchall()
        return [decode_sources(row) for row in rows]

    @app.patch("/api/tickets/{ticket_id}")
    def update_ticket(ticket_id: str, body: TicketUpdate, session=Depends(mutation)):
        auth.require_admin(session)
        with connect(settings.database) as db:
            condition = "owner=?" if session["is_demo"] else "owner LIKE 'user:%'"
            params = [body.status, ticket_id] + ([auth.owner(session)] if session["is_demo"] else [])
            changed = db.execute(f"UPDATE tickets SET status=? WHERE id=? AND {condition}", params).rowcount
        if not changed:
            raise HTTPException(404, "問い合わせが見つかりません。")
        audit(settings.database, "ticket_status_updated", session)
        return {"ok": True}

    @app.get("/api/admin/overview")
    def overview(session=Depends(auth.current_session)):
        auth.require_admin(session)
        with connect(settings.database) as db:
            # No other visitors' activity is disclosed to a demo session.
            if session["is_demo"]:
                usage = db.execute("SELECT model,status,input_tokens,output_tokens,cost,created FROM usage WHERE session=? ORDER BY created DESC LIMIT 50", (session["token_hash"],)).fetchall()
                logs = []
            else:
                usage = db.execute("SELECT model,status,input_tokens,output_tokens,cost,created FROM usage ORDER BY created DESC LIMIT 100").fetchall()
                logs = [dict(r) for r in db.execute("SELECT event,role,is_demo,created FROM audit ORDER BY created DESC LIMIT 30")]
        return {"usage": [dict(r) for r in usage], "audit": logs,
                "model": settings.llm_model if settings.llm_url else None,
                "daily_limit": settings.ai_daily_limit, "session_limit": settings.session_ai_limit,
                "embedding_model": settings.embedding_model or None,
                "pricing_configured": bool(settings.input_price and settings.output_price)}

    frontend = ROOT / "frontend/out"
    if frontend.is_dir():
        @app.get("/")
        def index():
            return FileResponse(frontend / "index.html", headers={"Cache-Control": "no-cache"})

        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    else:
        @app.get("/")
        def not_built():
            return JSONResponse({"detail": "先にfrontendで npm run build を実行してください。"}, status_code=503)

    app.add_middleware(BodyLimitMiddleware)
    return app


app = create_app()
