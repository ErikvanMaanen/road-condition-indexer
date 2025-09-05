import importlib
import sys

def test_connection_string_handles_special_chars(monkeypatch):
    env = {
        "AZURE_SQL_SERVER": "test-server.database.windows.net",
        "AZURE_SQL_PORT": "1433",
        "AZURE_SQL_USER": "test-user",
        "AZURE_SQL_PASSWORD": "p@ssword!",
        "AZURE_SQL_DATABASE": "testdb",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    captured = {}

    def fake_create_engine(url, *args, **kwargs):
        captured["url"] = url
        class DummyEngine:
            def __init__(self, url):
                self.url = url
            def connect(self):
                return None
        return DummyEngine(url)

    monkeypatch.setattr("sqlalchemy.create_engine", fake_create_engine)
    sys.modules.pop("database", None)
    db_module = importlib.import_module("database")

    dbm = db_module.DatabaseManager()
    dbm.get_engine()
    url = captured["url"]

    assert url.host == env["AZURE_SQL_SERVER"]
    assert url.username == env["AZURE_SQL_USER"]
    assert url.password == env["AZURE_SQL_PASSWORD"]
