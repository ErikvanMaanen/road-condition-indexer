"""Tests for the AI Features MCP test endpoint."""

import importlib
import os

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
        self.users = {
            "techno": {"id": 2, "username": "Techno", "role": main.ROLE_ADMIN, "password_hash": None},
        }

    def get_user_by_username(self, username):
        user = self.users.get(username.lower())
        return dict(user) if user else None

    def set_user_password_hash(self, user_id, password_hash):
        for user in self.users.values():
            if user["id"] == user_id:
                user["password_hash"] = password_hash

    def record_user_login(self, user_id):
        return None


class FakeMcpResponse:
    def __init__(self, payload, headers=None):
        self._payload = payload
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def load_main(monkeypatch):
    main = importlib.import_module("main")
    monkeypatch.setattr(main, "db_manager", FakeUserStore(main))
    return main


def login_admin(client):
    response = client.post(
        "/login",
        json={"username": "Techno", "password": "", "new_password": "techno-secret"},
    )
    assert response.status_code == 204


def test_mcp_test_endpoint_requires_admin(monkeypatch):
    main = load_main(monkeypatch)
    client = TestClient(main.app)

    response = client.post(
        "/ai/mcp/test",
        json={"url": "https://api.omi.me/v1/mcp/sse", "method": "tools/list"},
    )

    assert response.status_code == 401


def test_mcp_test_endpoint_lists_tools(monkeypatch):
    main = load_main(monkeypatch)
    posted_methods = []

    def fake_post(url, json, headers, timeout):
        posted_methods.append(json["method"])
        assert url == "https://api.omi.me/v1/mcp/sse"
        assert headers["Authorization"] == "Bearer omi_mcp_test"
        if json["method"] == "initialize":
            return FakeMcpResponse({"jsonrpc": "2.0", "id": "init", "result": {"capabilities": {}}})
        return FakeMcpResponse(
            {
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "tools": [
                        {
                            "name": "search_memories",
                            "description": "Search memories",
                            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
                        }
                    ]
                },
            }
        )

    monkeypatch.setattr(main.requests, "post", fake_post)
    client = TestClient(main.app)
    login_admin(client)

    response = client.post(
        "/ai/mcp/test",
        json={"url": "https://api.omi.me/v1/mcp/sse", "token": "omi_mcp_test", "method": "tools/list"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["result"]["result"]["tools"][0]["name"] == "search_memories"
    assert posted_methods == ["initialize", "tools/list"]


def test_mcp_test_endpoint_calls_selected_tool(monkeypatch):
    main = load_main(monkeypatch)
    captured_call = {}

    def fake_post(url, json, headers, timeout):
        if json["method"] == "tools/call":
            captured_call.update(json["params"])
            return FakeMcpResponse({"jsonrpc": "2.0", "id": "test", "result": {"content": [{"type": "text", "text": "ok"}]}})
        return FakeMcpResponse({"jsonrpc": "2.0", "id": "init", "result": {"capabilities": {}}})

    monkeypatch.setattr(main.requests, "post", fake_post)
    client = TestClient(main.app)
    login_admin(client)

    response = client.post(
        "/ai/mcp/test",
        json={
            "url": "https://api.omi.me/v1/mcp/sse",
            "method": "tools/call",
            "tool_name": "search_memories",
            "arguments": {"query": "road", "limit": 2},
        },
    )

    assert response.status_code == 200
    assert captured_call == {"name": "search_memories", "arguments": {"query": "road", "limit": 2}}
    assert response.json()["result"]["result"]["content"][0]["text"] == "ok"
