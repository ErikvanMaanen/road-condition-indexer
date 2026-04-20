"""Tests for Dumpert player page auth and seamless playback UI."""

import importlib
import os

import pytest
from fastapi.dependencies import utils as fastapi_utils

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

REQUIRED_VARS = {
    'AZURE_SQL_SERVER': 'stub.server.local',
    'AZURE_SQL_PORT': '1433',
    'AZURE_SQL_USER': 'test',
    'AZURE_SQL_PASSWORD': 'secret',
    'AZURE_SQL_DATABASE': 'testdb',
}

for key, value in REQUIRED_VARS.items():
    os.environ.setdefault(key, value)


def _load_main(monkeypatch):
    monkeypatch.setattr(fastapi_utils, 'ensure_multipart_is_installed', lambda: None)
    return importlib.import_module('main')


def test_dumpert_player_page_exposes_seamless_background_stream_flow(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, 'is_authenticated', lambda _request: True)

    client = TestClient(main.app)
    response = client.get('/dumpert-player.html')

    assert response.status_code == 200
    assert 'Seamless player' in response.text
    assert 'achtergrond-check (diagnostics + byte-range prewarm)' in response.text
    assert 'Seamless afspelen' in response.text
    assert 'Start alle 10 oplossingen' not in response.text
