"""Tests for Dumpert bootstrap stream extraction and background strategy payload."""

import importlib
import json
import os

import pytest
from fastapi.dependencies import utils as fastapi_utils

pytest.importorskip("httpx")
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


def _load_main(monkeypatch):
    monkeypatch.setattr(fastapi_utils, "ensure_multipart_is_installed", lambda: None)
    return importlib.import_module("main")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.content = json.dumps(payload).encode("utf-8")
        self.headers = {"content-type": "application/json"}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_bootstrap_returns_first_item_and_stream_candidates(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, "is_authenticated", lambda _request: True)

    upstream_payload = {
        "items": [
            {
                "id": "100_first",
                "title": "First one",
                "media": {
                    "variants": {
                        "mp4": "https://media.dumpert.nl/video/100_first.mp4",
                        "hls": "https://media.dumpert.nl/video/100_first.m3u8",
                    }
                },
            },
            {"id": "200_second", "title": "Second one"},
        ]
    }
    monkeypatch.setattr(main.requests, "get", lambda *_args, **_kwargs: _FakeResponse(upstream_payload))

    client = TestClient(main.app)
    response = client.get("/api/dumpert/bootstrap?page=0&nsfw=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["item"]["id"] == "100_first"
    assert payload["preferred_stream"] == "https://media.dumpert.nl/video/100_first.mp4"
    assert payload["stream_sources"]["m3u8"] == "https://media.dumpert.nl/video/100_first.m3u8"
    assert payload["source_url_count"] >= 2
    names = [entry["name"] for entry in payload["stream_candidates"]]
    assert "proxy-prewarm-mp4" in names
    assert "source-direct-m3u8" in names


def test_bootstrap_detects_ad_signals(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, "is_authenticated", lambda _request: True)

    upstream_payload = {
        "items": [
            {
                "id": "ad_case",
                "title": "Has ad marker",
                "media": {"mp4": "https://media.dumpert.nl/vast/ad_preroll.mp4"},
            }
        ]
    }
    monkeypatch.setattr(main.requests, "get", lambda *_args, **_kwargs: _FakeResponse(upstream_payload))

    client = TestClient(main.app)
    response = client.get("/api/dumpert/bootstrap?page=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ad_signals"]["detected"] is True
    assert payload["ad_signals"]["matches"]
