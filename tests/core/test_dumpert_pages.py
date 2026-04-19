"""Tests for Dumpert static pages and auth gate behavior."""

import importlib
import os

from fastapi.dependencies import utils as fastapi_utils
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


def test_dumpert_player_page_requires_auth(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, 'is_authenticated', lambda _request: False)

    client = TestClient(main.app)
    response = client.get('/dumpert-player.html', follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers['location'] == '/static/login.html?next=/dumpert-player.html'


def test_dumpert_player_page_serves_when_authenticated(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, 'is_authenticated', lambda _request: True)

    client = TestClient(main.app)
    response = client.get('/dumpert-player.html')

    assert response.status_code == 200
    assert 'Dumpert Player' in response.text


def test_dumpert_loader_page_still_serves(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, 'is_authenticated', lambda _request: True)

    client = TestClient(main.app)
    response = client.get('/dumpert.html')

    assert response.status_code == 200
    assert 'Dumpert Top Loader' in response.text


def test_dumpert_media_diagnostics_rejects_non_dumpert_hosts(monkeypatch):
    main = _load_main(monkeypatch)
    client = TestClient(main.app)

    response = client.get('/api/dumpert/media-diagnostics', params={'url': 'https://example.com/video.mp4'})

    assert response.status_code == 400
    assert response.json()['detail'] == 'Media URL host not allowed'


def test_dumpert_media_proxy_rejects_bad_scheme(monkeypatch):
    main = _load_main(monkeypatch)
    client = TestClient(main.app)

    response = client.get('/api/dumpert/media-proxy', params={'url': 'file:///tmp/test.mp4'})

    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid media URL scheme'
