import io
from dataclasses import replace

from fastapi.testclient import TestClient
from helpdesk import rag
from helpdesk.main import create_app
from pypdf import PdfWriter

from .conftest import login_demo, login_real
from .test_rag import ask


def test_body_limit_handles_missing_length(client):
    headers = login_demo(client)

    def chunks():
        for _ in range(23):
            yield b"x" * 100000

    response = client.post("/api/chat", content=chunks(), headers={**headers, "Content-Type": "application/json"})
    assert response.status_code == 413


def test_secure_cookie_and_persistent_expiration(settings):
    with TestClient(create_app(replace(settings, secure_cookie=True)), base_url="https://testserver") as client:
        response = client.post("/api/auth/login", json={"email": "admin@example.test", "password": "Admin-Long-Password!", "remember": True})
        cookie = response.headers["set-cookie"].lower()
        assert "secure" in cookie and "max-age=2592000" in cookie
        assert client.get("/api/auth/me").status_code == 200


def test_embedding_path_still_uses_authorized_candidates(settings, monkeypatch):
    import json

    settings = replace(settings, llm_url="http://proxy.test/v1", llm_key="key", embedding_model="embedding-test")
    routes = []

    def gateway(_settings, route, payload):
        routes.append(route)
        assert "DEMO-ADMIN-ONLY-742" not in json.dumps(payload)
        if route == "embeddings":
            return {"data": [{"index": i, "embedding": [1, 0, 1]} for i in range(len(payload["input"]))]}
        source = json.loads(payload["messages"][1]["content"])["untrusted_manuals"][0]
        return {"choices": [{"message": {"content": json.dumps({"status": "answered", "answer": "VPNを再起動します。", "source_ids": [source["id"]]})}}]}

    monkeypatch.setattr(rag, "gateway", gateway)
    with TestClient(create_app(settings)) as client:
        answer = ask(client, login_demo(client))
        assert answer["retrieval"] == "tfidf+embedding-rerank"
        assert routes == ["embeddings", "chat/completions"]


def test_invalid_provider_json_falls_back(settings, monkeypatch):
    settings = replace(settings, llm_url="http://proxy.test/v1", llm_key="key")
    monkeypatch.setattr(rag, "gateway", lambda *_: {"choices": [{"message": {"content": "not json"}}]})
    with TestClient(create_app(settings)) as client:
        assert ask(client, login_demo(client))["reason"] == "provider_error"


def test_blank_pdf_is_rejected_and_no_document_added(client):
    headers = login_real(client)
    count = len(client.get("/api/documents").json())
    pdf = PdfWriter()
    pdf.add_blank_page(width=100, height=100)
    content = io.BytesIO()
    pdf.write(content)
    response = client.post("/api/documents/pdf", files={"file": ("blank.pdf", content.getvalue())}, headers=headers)
    assert response.status_code == 422
    assert len(client.get("/api/documents").json()) == count


def test_demo_can_be_disabled(settings):
    with TestClient(create_app(replace(settings, demo=False))) as client:
        assert client.post("/api/auth/demo", json={"role": "admin"}).status_code == 404


def test_chat_rate_limit(client):
    headers = login_demo(client)
    for _ in range(20):
        ask(client, headers, "VPNにつながらない")
    assert client.post("/api/chat", json={"question": "VPNにつながらない"}, headers=headers).status_code == 429
