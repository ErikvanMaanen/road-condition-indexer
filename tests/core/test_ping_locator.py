"""Unit tests for the ping executable resolution helper."""
import stat
from pathlib import Path

import pytest

import main


def _make_executable(tmp_path: Path, name: str = "custom-ping") -> Path:
    candidate = tmp_path / name
    candidate.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    candidate.chmod(candidate.stat().st_mode | stat.S_IEXEC)
    return candidate


def test_find_ping_executable_prefers_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ping = _make_executable(tmp_path)
    monkeypatch.delenv("PING_EXECUTABLE", raising=False)
    monkeypatch.delenv("PING_PATH", raising=False)

    result = main._find_ping_executable({"ping_path": str(fake_ping)})
    assert result == str(fake_ping)


def test_find_ping_executable_uses_environment_variable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ping = _make_executable(tmp_path, name="env-ping")
    monkeypatch.setenv("PING_EXECUTABLE", str(fake_ping))
    monkeypatch.delenv("PING_PATH", raising=False)

    result = main._find_ping_executable({})
    assert result == str(fake_ping)


def test_find_ping_executable_falls_back_to_bundled_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    bundled_ping = main.BUNDLED_PING_DIR / "ping"
    assert bundled_ping.exists(), "Bundled ping executable must be present"

    monkeypatch.delenv("PING_EXECUTABLE", raising=False)
    monkeypatch.delenv("PING_PATH", raising=False)
    monkeypatch.setenv("PATH", "")

    result = main._find_ping_executable({})
    assert result == str(bundled_ping.resolve())

