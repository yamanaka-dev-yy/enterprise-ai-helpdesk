from fastapi.testclient import TestClient
from helpdesk.main import create_app

from .conftest import login_demo, login_real
from .test_rag import ask


def test_demo_tickets_are_isolated_and_deleted_on_logout(client, settings):
    h1 = login_demo(client, "admin")
    result = ask(client, h1)
    issue = client.post("/api/tickets", json={"answer_id": result["id"]}, headers=h1).json()
    assert len(client.get("/api/tickets").json()) == 1
    with TestClient(create_app(settings)) as other:
        h2 = login_demo(other, "admin")
        assert other.get("/api/tickets").json() == []
        assert other.post("/api/tickets", json={"answer_id": result["id"]}, headers=h2).status_code == 404
        assert other.patch(f"/api/tickets/{issue['id']}", json={"status": "closed"}, headers=h2).status_code == 404
        assert other.get("/api/admin/overview").json()["audit"] == []
    assert client.post("/api/auth/logout", headers=h1).status_code == 200


def test_ticket_creation_is_idempotent_and_copies_evidence(client):
    headers = login_demo(client)
    result = ask(client, headers)
    first = client.post("/api/tickets", json={"answer_id": result["id"]}, headers=headers)
    second = client.post("/api/tickets", json={"answer_id": result["id"]}, headers=headers)
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["sources"] == result["sources"]
    assert client.patch(f"/api/tickets/{first.json()['id']}", json={"status": "closed"}, headers=headers).status_code == 403


def test_normal_admin_can_manage_normal_ticket_but_not_demo(client, settings):
    headers = login_real(client, "employee")
    result = ask(client, headers)
    issue = client.post("/api/tickets", json={"answer_id": result["id"]}, headers=headers).json()
    admin_headers = login_real(client)
    assert issue["id"] in [row["id"] for row in client.get("/api/tickets").json()]
    assert client.patch(f"/api/tickets/{issue['id']}", json={"status": "closed"}, headers=admin_headers).status_code == 200
    with TestClient(create_app(settings)) as other:
        login_real(other, "employee")
        assert other.get("/api/tickets").json()[0]["status"] == "closed"


def test_demo_admin_cannot_write_shared_manuals(client):
    headers = login_demo(client, "admin")
    body = {"title": "Test", "text": "A fictional test document with at least twenty characters.", "role": "employee"}
    assert client.post("/api/documents", json=body, headers=headers).status_code == 403
    assert client.put("/api/documents/account", json=body, headers=headers).status_code == 403
    assert client.delete("/api/documents/account", headers=headers).status_code == 403
    assert client.post("/api/documents/pdf", files={"file": ("test.pdf", b"%PDF-test")}, headers=headers).status_code == 403


def test_document_crud_and_search_updates(client):
    headers = login_real(client)
    body = {"title": "試験用プリンターマニュアル", "text": "# プリンターの設定\nプリンターを設定するには管理画面でデバイスを追加してください。架空の登録手順です。", "role": "employee"}
    response = client.post("/api/documents", json=body, headers=headers)
    assert response.status_code == 201
    document_id = response.json()["id"]
    assert any(d["id"] == document_id for d in client.get("/api/documents").json())
    result = ask(client, headers, "プリンターの設定")
    assert result["sources"][0]["document_id"] == document_id
    body["role"] = "admin"
    assert client.put(f"/api/documents/{document_id}", json=body, headers=headers).status_code == 200
    employee_headers = login_demo(client)
    assert document_id not in [d["id"] for d in client.get("/api/documents").json()]
    assert client.delete(f"/api/documents/{document_id}", headers=employee_headers).status_code == 403
    headers = login_real(client)
    assert client.delete(f"/api/documents/{document_id}", headers=headers).status_code == 200
    assert ask(client, headers, "プリンターの設定")["status"] == "withheld"


def test_invalid_pdf_is_rejected(client):
    headers = login_real(client)
    response = client.post("/api/documents/pdf", files={"file": ("fake.pdf", b"not a pdf")}, headers=headers)
    assert response.status_code == 422
