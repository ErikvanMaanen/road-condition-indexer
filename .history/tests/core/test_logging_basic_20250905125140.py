"""Basic logging utility tests.

These operate only on in-memory helpers and avoid real DB writes by
ensuring db_manager stub methods no-op if connection fails. The DatabaseManager
instantiation will not attempt a connection until first engine use.
"""
import importlib
import os

DUMMY_ENV = {
    'AZURE_SQL_SERVER': 'dummy.server.local',
    'AZURE_SQL_PORT': '1433',
    'AZURE_SQL_USER': 'user',
    'AZURE_SQL_PASSWORD': 'pass',
    'AZURE_SQL_DATABASE': 'testdb',
}
for k, v in DUMMY_ENV.items():
    os.environ.setdefault(k, v)

from log_utils import (DEBUG_LOG, LogCategory, log_debug, log_error, log_info,
                       log_warning)


def test_debug_ring_buffer_appends():
    start_len = len(DEBUG_LOG)
    log_debug("unit test debug message")
    assert len(DEBUG_LOG) == start_len + 1


def test_info_warning_error_no_exceptions():
    # These should not raise
    log_info("info message", LogCategory.GENERAL)
    log_warning("warn message", LogCategory.GENERAL)
    log_error("error message", LogCategory.GENERAL, include_stack=False)
