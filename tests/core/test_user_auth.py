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

    def list_users(self):
        return [
            {**user, "password_set": bool(user.get("password_hash"))}
            for user in sorted(self.users.values(), key=lambda row: row["username"].lower())
        ]

    def get_user_by_id(self, user_id):
        for user in self.users.values():
            if user["id"] == user_id:
                return dict(user)
        return None

    def create_user(self, username, role, password_hash=None):
        user_id = max(user["id"] for user in self.users.values()) + 1
        user = {"id": user_id, "username": username, "role": role, "password_hash": password_hash}
        self.users[username.lower()] = user
        return dict(user)

    def update_user(self, user_id, username, role):
        old_key = None
        for key, user in self.users.items():
            if user["id"] == user_id:
                old_key = key
                break
        if old_key is None:
            return None
        user = self.users.pop(old_key)
        user["username"] = username
        user["role"] = role
        self.users[username.lower()] = user
        return dict(user)

    def clear_user_password(self, user_id):
        self.set_user_password_hash(user_id, None)

    def delete_user(self, user_id):
        for key, user in list(self.users.items()):
            if user["id"] == user_id:
                del self.users[key]


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


def test_admin_can_manage_users(monkeypatch):
    main, store = load_main(monkeypatch)
    client = TestClient(main.app)
    client.post("/login", json={"username": "Techno", "password": "", "new_password": "techno-secret"})

    create_response = client.post(
        "/manage/users",
        json={"username": "Alex", "role": "User", "password": "alex-secret"},
    )

    assert create_response.status_code == 201
    created = create_response.json()["user"]
    assert created["username"] == "Alex"
    assert created["password_set"] is True

    update_response = client.put(
        f"/manage/users/{created['id']}",
        json={"username": "Alex Admin", "role": "Admin"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["user"]["role"] == "Admin"

    reset_response = client.post(f"/manage/users/{created['id']}/password", json={})

    assert reset_response.status_code == 200
    assert store.users["alex admin"]["password_hash"] is None

    delete_response = client.delete(f"/manage/users/{created['id']}")

    assert delete_response.status_code == 200
    assert "alex admin" not in store.users


def test_admin_cannot_delete_own_user(monkeypatch):
    main, _store = load_main(monkeypatch)
    client = TestClient(main.app)
    client.post("/login", json={"username": "Techno", "password": "", "new_password": "techno-secret"})

    response = client.delete("/manage/users/2")

    assert response.status_code == 400
