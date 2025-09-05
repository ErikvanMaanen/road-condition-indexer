"""Tests for minimal DatabaseManager behavior without real DB connection.

We only exercise attribute logic that does not require an actual SQL Server.
"""
import importlib
import os

# Ensure required environment variables (dummy values)
ENV = {
    'AZURE_SQL_SERVER': 'dummy.server.local',
    'AZURE_SQL_PORT': '1433',
    'AZURE_SQL_USER': 'user',
    'AZURE_SQL_PASSWORD': 'pass',
    'AZURE_SQL_DATABASE': 'testdb',
}
for k, v in ENV.items():
    os.environ.setdefault(k, v)

def test_database_manager_use_sqlserver_true():
    db = importlib.import_module('database')
    manager = db.DatabaseManager()
    assert manager.use_sqlserver is True


def test_database_manager_log_level_change():
    db = importlib.import_module('database')
    manager = db.DatabaseManager()
    orig = manager.log_level
    # Change level and validate
    from log_utils import LogLevel
    manager.set_log_level(LogLevel.DEBUG)
    assert manager.log_level == LogLevel.DEBUG
    assert manager.log_level != orig
