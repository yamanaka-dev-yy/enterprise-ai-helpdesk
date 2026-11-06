from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from helpdesk.config import Settings
from helpdesk.main import create_app


@pytest.fixture
def settings(tmp_path):
    return replace(Settings(), database=str(tmp_path / "test.sqlite3"), secure_cookie=False,
                   admin_email="admin@example.test", admin_password="Admin-Long-Password!",
                   employee_email="employee@example.test", employee_password=" Employee-Password! ",
                   demo=True, llm_url="", llm_key="", embedding_model="")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


def login_demo(client, role="employee"):
    response = client.post("/api/auth/demo", json={"role": role})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def login_real(client, role="admin", remember=False):
    password = "Admin-Long-Password!" if role == "admin" else " Employee-Password! "
    response = client.post("/api/auth/login", json={"email": f"{role}@example.test", "password": password, "remember": remember})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}
