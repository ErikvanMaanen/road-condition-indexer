"""Tests for Dumpert media proxy playlist rewriting."""

import importlib
import os

from fastapi.dependencies import utils as fastapi_utils

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


def test_rewrite_m3u8_playlist_rewrites_segment_and_key_urls(monkeypatch):
    main = _load_main(monkeypatch)
    source_url = "https://media.dumpert.nl/dmp/media/video/x/y/z/270/index.m3u8"
    playlist = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-KEY:METHOD=AES-128,URI="key.bin"
#EXTINF:4.000,
chunk_001.ts
https://media.dumpert.nl/direct/chunk_002.ts
"""

    rewritten = main._rewrite_m3u8_playlist(playlist, source_url)

    assert '/api/dumpert/media-proxy?url=https%3A%2F%2Fmedia.dumpert.nl%2Fdmp%2Fmedia%2Fvideo%2Fx%2Fy%2Fz%2F270%2Fchunk_001.ts' in rewritten
    assert '/api/dumpert/media-proxy?url=https%3A%2F%2Fmedia.dumpert.nl%2Fdirect%2Fchunk_002.ts' in rewritten
    assert 'URI="/api/dumpert/media-proxy?url=https%3A%2F%2Fmedia.dumpert.nl%2Fdmp%2Fmedia%2Fvideo%2Fx%2Fy%2Fz%2F270%2Fkey.bin"' in rewritten
