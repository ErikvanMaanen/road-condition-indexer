"""User-management authentication tests."""

import importlib
import os

import pytest
from fastapi.testclient import TestClient

REQUIRED_VARS = {
    "AZURE_SQL_SERVER": "stub.server.local",
    "AZURE_SQL_PORT": "1433",
    "AZURE_SQL_USER": "test",
    "AZURE_SQL_PASSWORD": "secret",
    "AZURE_SQL_DATABASE": "testdb",
}

for key, value in REQUIRED_VARS.items():
    os.environ.setdefault(key, value)


class FakeUserStore:
    def __init__(self, main):
        self.main = main
        self.users = {
            "fiets": {"id": 1, "username": "Fiets", "role": main.ROLE_USER, "password_hash": None},
            "techno": {"id": 2, "username": "Techno", "role": main.ROLE_ADMIN, "password_hash": None},
        }

    def get_user_by_username(self, username):
        user = self.users.get(username.lower())
        return dict(user) if user else None

    def set_user_password_hash(self, user_id, password_hash):
        for user in self.users.values():
            if user["id"] == user_id:
                user["password_hash"] = password_hash
                return

    def record_user_login(self, user_id):
        return None


def load_main(monkeypatch):
    main = importlib.import_module("main")
    fake_store = FakeUserStore(main)
    monkeypatch.setattr(main, "db_manager", fake_store)
    return main, fake_store


def test_initial_user_sets_password_and_accesses_main_page(monkeypatch):
    main, store = load_main(monkeypatch)
    client = TestClient(main.app)

    response = client.post(
        "/login",
        json={"username": "Fiets", "password": "", "new_password": "fiets-secret"},
    )

    assert response.status_code == 204
    assert store.users["fiets"]["password_hash"].startswith("pbkdf2_sha256$")
    assert client.get("/auth_check").status_code == 204


def test_user_cannot_access_admin_role(monkeypatch):
    main, _store = load_main(monkeypatch)
    client = TestClient(main.app)
    client.post("/login", json={"username": "Fiets", "password": "", "new_password": "fiets-secret"})

    response = client.get("/auth_check?role=Admin")

    assert response.status_code == 403


def test_admin_can_access_admin_role(monkeypatch):
    main, _store = load_main(monkeypatch)
    client = TestClient(main.app)
    client.post("/login", json={"username": "Techno", "password": "", "new_password": "techno-secret"})

    response = client.get("/auth_check?role=Admin")

    assert response.status_code == 204
