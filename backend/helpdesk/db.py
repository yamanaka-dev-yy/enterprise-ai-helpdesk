import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .seed import DOCUMENTS


@contextmanager
def connect(path):
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('employee','admin'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, user_id TEXT, role TEXT NOT NULL,
            is_demo INTEGER NOT NULL, csrf TEXT NOT NULL, expires REAL NOT NULL,
            created REAL NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, text TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('employee','admin')), updated REAL NOT NULL,
            seeded INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS answers (
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, question TEXT NOT NULL,
            answer TEXT NOT NULL, sources TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, answer_id TEXT NOT NULL,
            question TEXT NOT NULL, answer TEXT NOT NULL, sources TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open', created REAL NOT NULL,
            UNIQUE(owner,answer_id)
        );
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY, event TEXT NOT NULL, role TEXT,
            is_demo INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY, session TEXT NOT NULL, model TEXT NOT NULL,
            status TEXT NOT NULL, input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0, cost REAL, created REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS limits (
            bucket TEXT NOT NULL, key TEXT NOT NULL, window INTEGER NOT NULL,
            count INTEGER NOT NULL, PRIMARY KEY(bucket,key,window)
        );
        """)
        for doc in DOCUMENTS:
            db.execute(
                "INSERT OR IGNORE INTO documents (id,title,text,role,updated,seeded) VALUES (?,?,?,?,?,1)",
                (doc["id"], doc["title"], doc["text"], doc["role"], time.time()),
            )


def audit(path, event, session=None):
    with connect(path) as db:
        db.execute("INSERT INTO audit(event,role,is_demo,created) VALUES (?,?,?,?)",
                   (event, session["role"] if session else None,
                    session["is_demo"] if session else 0, time.time()))


def accessible_documents(path, role):
    with connect(path) as db:
        # Restrict BEFORE scoring, embeddings or model context construction.
        return [dict(r) for r in db.execute(
            "SELECT * FROM documents WHERE role='employee' OR ?='admin' ORDER BY title", (role,)
        )]


def consume_limit(path, bucket, key, maximum, seconds=60):
    now = time.time()
    window = int(now // seconds)
    with connect(path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT count FROM limits WHERE bucket=? AND key=? AND window=?",
                         (bucket, key, window)).fetchone()
        if row and row["count"] >= maximum:
            return False
        db.execute("INSERT INTO limits VALUES (?,?,?,1) ON CONFLICT(bucket,key,window) DO UPDATE SET count=count+1",
                   (bucket, key, window))
        db.execute("DELETE FROM limits WHERE window < ? AND bucket=?", (window - 2, bucket))
        return True


def prune(path):
    now = time.time()
    with connect(path) as db:
        # Demo conversation data survives at most 24 h; logs contain metadata only.
        db.execute("DELETE FROM sessions WHERE expires<?", (now,))
        db.execute("DELETE FROM answers WHERE created<?", (now - 86400,))
        db.execute("DELETE FROM tickets WHERE owner LIKE 'demo:%' AND created<?", (now - 86400,))
        db.execute("DELETE FROM audit WHERE created<?", (now - 30 * 86400,))
        db.execute("DELETE FROM usage WHERE created<?", (now - 30 * 86400,))


def decode_sources(row):
    data = dict(row)
    data["sources"] = json.loads(data["sources"])
    data.pop("owner", None)
    return data
