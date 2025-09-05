"""Basic import sanity tests for minimal suite.

These tests ensure core modules import without raising unexpected exceptions.
Environment variables required by database.py are temporarily set to dummy values
so import side-effects succeed without a real SQL Server.
"""
import os
import importlib
import types

REQUIRED_VARS = {
    'AZURE_SQL_SERVER': 'dummy.server.local',
    'AZURE_SQL_PORT': '1433',
    'AZURE_SQL_USER': 'user',
    'AZURE_SQL_PASSWORD': 'pass',
    'AZURE_SQL_DATABASE': 'testdb',
}

for k, v in REQUIRED_VARS.items():
    os.environ.setdefault(k, v)

def test_import_database_module():
    db_mod = importlib.import_module('database')
    assert hasattr(db_mod, 'DatabaseManager')


def test_import_log_utils():
    log_mod = importlib.import_module('log_utils')
    for name in ['log_debug', 'log_info', 'log_warning', 'log_error']:
        assert hasattr(log_mod, name)


def test_import_main_lite():
    # Import only first portion of main by using importlib; main is large so just ensure module object loads.
    main_mod = importlib.import_module('main')
    assert isinstance(main_mod, types.ModuleType)
