"""Unit tests for memo endpoint logic without HTTP dependencies."""

import os
from typing import List, Optional

import pytest
from fastapi import HTTPException

REQUIRED_VARS = {
    'AZURE_SQL_SERVER': 'stub.server.local',
    'AZURE_SQL_PORT': '1433',
    'AZURE_SQL_USER': 'test',
    'AZURE_SQL_PASSWORD': 'secret',
    'AZURE_SQL_DATABASE': 'testdb',
}

for key, value in REQUIRED_VARS.items():
    os.environ.setdefault(key, value)


class StubMemoDB:
    """Simple in-memory replacement for the database manager during tests."""

    def __init__(self) -> None:
        self._memos: List[dict] = [
            {
                'id': 2,
                'content': 'Nieuwere memo',
                'created_at': '2024-01-02T10:00:00+00:00',
                'updated_at': '2024-01-02T10:00:00+00:00',
            },
            {
                'id': 1,
                'content': 'Oude memo',
                'created_at': '2024-01-01T08:00:00+00:00',
                'updated_at': '2024-01-01T08:00:00+00:00',
            },
        ]

    def get_memos(self, limit: Optional[int] = None):
        if limit:
            return self._memos[:limit]
        return list(self._memos)

    def create_memo(self, content: str) -> dict:
        next_id = max((memo['id'] for memo in self._memos), default=0) + 1
        memo = {
            'id': next_id,
            'content': content,
            'created_at': '2024-01-03T12:00:00+00:00',
            'updated_at': '2024-01-03T12:00:00+00:00',
        }
        self._memos.insert(0, memo)
        return memo

    def update_memo(self, memo_id: int, content: str) -> Optional[dict]:
        for memo in self._memos:
            if memo['id'] == memo_id:
                memo['content'] = content
                memo['updated_at'] = '2024-01-04T09:00:00+00:00'
                return memo
        return None


@pytest.fixture()
def memo_app(monkeypatch):
    import importlib

    main = importlib.import_module('main')
    stub = StubMemoDB()
    monkeypatch.setattr(main, 'db_manager', stub)
    return main, stub


def test_list_memos_returns_payload(memo_app):
    main, stub = memo_app
    payload = main.list_memos(limit=None)
    assert payload['status'] == 'ok'
    assert len(payload['memos']) == len(stub._memos)


def test_create_memo_trims_content(memo_app):
    main, stub = memo_app
    result = main.create_memo(main.MemoCreateRequest(content='  Nieuwe memo  '))
    assert result['status'] == 'ok'
    assert stub._memos[0]['content'] == 'Nieuwe memo'


def test_create_memo_rejects_empty(memo_app):
    main, _ = memo_app
    with pytest.raises(HTTPException) as exc:
        main.create_memo(main.MemoCreateRequest(content='   '))
    assert exc.value.status_code == 400


def test_update_memo_success(memo_app):
    main, stub = memo_app
    result = main.update_memo(1, main.MemoUpdateRequest(content='Bijgewerkte memo'))
    assert result['status'] == 'ok'
    assert stub._memos[-1]['content'] == 'Bijgewerkte memo'


def test_update_memo_not_found(memo_app):
    main, _ = memo_app
    with pytest.raises(HTTPException) as exc:
        main.update_memo(999, main.MemoUpdateRequest(content='Bestaat niet'))
    assert exc.value.status_code == 404
