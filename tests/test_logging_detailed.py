#!/usr/bin/env python3
"""
Detailed test script for the new logging functionality.
This script tests each component separately to identify where the hang occurs.
"""

import sys
import os
import time
import traceback
from datetime import datetime
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("ROAD CONDITION INDEXER - DETAILED LOGGING TEST")
print("=" * 80)
print(f"Test started at: {datetime.now()}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[0]}")
print()

def test_step(step_name, test_func):
    """Run a test step with detailed error handling."""
    print(f"🔍 STEP: {step_name}")
    print("-" * 60)
    start_time = time.time()
    
    try:
        result = test_func()
        elapsed = time.time() - start_time
        print(f"✅ SUCCESS: {step_name} completed in {elapsed:.2f}s")
        print(f"   Result: {result}")
        print()
        return True, result
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ FAILED: {step_name} failed after {elapsed:.2f}s")
        print(f"   Error: {e}")
        print(f"   Type: {type(e).__name__}")
        print(f"   Traceback:")
        traceback.print_exc(limit=5)
        print()
        return False, None

def test_imports():
    """Test importing modules."""
    print("Testing basic imports...")
    
    # Test standard library imports
    import json
    import sqlite3
    import logging
    print("✓ Standard library imports successful")
    
    # Test third party imports
    try:
        import pytz
        print("✓ pytz import successful")
    except ImportError as e:
        print(f"⚠️ pytz import failed: {e}")
    
    try:
        import pyodbc
        print("✓ pyodbc import successful")
    except ImportError as e:
        print(f"⚠️ pyodbc import failed: {e}")
    
    # Test FastAPI import
    try:
        from fastapi import FastAPI
        print("✓ FastAPI import successful")
    except ImportError as e:
        print(f"⚠️ FastAPI import failed: {e}")
    
    return "Imports completed"

def test_database_module():
    """Test importing the database module."""
    print("Testing database module import...")
    
    try:
        from database import DatabaseManager, LogLevel, LogCategory, TABLE_USER_ACTIONS
        print("✓ Database module imported successfully")
        print(f"✓ LogLevel enum: {list(LogLevel)}")
        print(f"✓ LogCategory enum: {list(LogCategory)}")
        print(f"✓ New table constant: {TABLE_USER_ACTIONS}")
        return "Database module import successful"
    except Exception as e:
        print(f"❌ Database module import failed: {e}")
        raise

def test_database_manager_creation():
    """Test creating a DatabaseManager instance."""
    print("Testing DatabaseManager creation...")
    
    from database import DatabaseManager, LogLevel, LogCategory
    
    # Create with default settings
    db_manager = DatabaseManager()
    print(f"✓ DatabaseManager created with default settings")
    print(f"✓ Using SQL Server: {db_manager.use_sqlserver}")
    print(f"✓ Log level: {db_manager.log_level}")
    print(f"✓ Log categories: {[c.value for c in db_manager.log_categories]}")
    
    return f"DatabaseManager created (SQL Server: {db_manager.use_sqlserver})"

def test_database_connection():
    """Test database connection."""
    print("Testing database connection...")
    
    from database import DatabaseManager
    
    db_manager = DatabaseManager()
    
    try:
        conn = db_manager.get_connection()
        print(f"✓ Database connection successful: {type(conn)}")
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"✓ Basic query successful: {result}")
        
        conn.close()
        print("✓ Connection closed successfully")
        
        return "Database connection test passed"
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

def test_table_initialization():
    """Test table initialization."""
    print("Testing table initialization...")
    
    from database import DatabaseManager
    
    db_manager = DatabaseManager()
    
    try:
        print("Starting init_tables()...")
        start_time = time.time()
        
        db_manager.init_tables()
        
        elapsed = time.time() - start_time
        print(f"✓ Table initialization completed in {elapsed:.2f}s")
        
        # Verify tables exist
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if db_manager.use_sqlserver:
            cursor.execute("SELECT name FROM sys.tables WHERE name LIKE 'RCI_%'")
        else:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'RCI_%'")
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ Tables found: {tables}")
        
        conn.close()
        
        return f"Tables initialized: {tables}"
    except Exception as e:
        print(f"❌ Table initialization failed: {e}")
        raise

def test_user_action_logging():
    """Test user action logging."""
    print("Testing user action logging...")
    
    from database import DatabaseManager
    
    db_manager = DatabaseManager()
    
    try:
        # Ensure tables are initialized
        db_manager.init_tables()
        
        # Test logging a user action
        db_manager.log_user_action(
            action_type="TEST_ACTION",
            action_description="Test user action logging functionality",
            user_ip="127.0.0.1",
            user_agent="Test-Agent/1.0",
            device_id="test_device_001",
            session_id="test_session_123",
            additional_data={"test": True, "timestamp": datetime.now().isoformat()},
            success=True
        )
        
        print("✓ User action logged successfully")
        
        # Try to retrieve the action
        actions = db_manager.get_user_actions(limit=1)
        print(f"✓ Retrieved {len(actions)} user actions")
        
        if actions:
            latest_action = actions[0]
            print(f"✓ Latest action: {latest_action.get('action_type')} - {latest_action.get('action_description')}")
        
        return f"User action logging test passed ({len(actions)} actions retrieved)"
    except Exception as e:
        print(f"❌ User action logging failed: {e}")
        raise

def test_sql_operation_logging():
    """Test SQL operation logging."""
    print("Testing SQL operation logging...")
    
    from database import DatabaseManager
    
    db_manager = DatabaseManager()
    
    try:
        # Ensure tables are initialized
        db_manager.init_tables()
        
        # Test logging an SQL operation
        db_manager.log_sql_operation(
            operation_type="SELECT",
            query="SELECT COUNT(*) FROM RCI_bike_data",
            params=None,
            result_count=1,
            execution_time_ms=15.5,
            success=True,
            device_id=None
        )
        
        print("✓ SQL operation logged successfully")
        
        # Retrieve debug logs to see the SQL operation log
        debug_logs = db_manager.get_debug_logs(limit=5)
        sql_logs = [log for log in debug_logs if log.get('category') == 'SQL_OPERATION']
        
        print(f"✓ Found {len(sql_logs)} SQL operation logs")
        
        return f"SQL operation logging test passed ({len(sql_logs)} SQL logs found)"
    except Exception as e:
        print(f"❌ SQL operation logging failed: {e}")
        raise

def test_startup_event_logging():
    """Test startup event logging."""
    print("Testing startup event logging...")
    
    from database import DatabaseManager
    
    db_manager = DatabaseManager()
    
    try:
        # Ensure tables are initialized
        db_manager.init_tables()
        
        # Test logging a startup event
        db_manager.log_startup_event(
            event_type="TEST_STARTUP",
            event_description="Test startup event logging functionality",
            success=True,
            additional_data={"component": "test_suite", "version": "1.0"}
        )
        
        print("✓ Startup event logged successfully")
        
        # Retrieve startup-related user actions
        startup_actions = db_manager.get_user_actions(action_type_filter="STARTUP_TEST_STARTUP", limit=1)
        print(f"✓ Found {len(startup_actions)} startup events")
        
        return f"Startup event logging test passed ({len(startup_actions)} events found)"
    except Exception as e:
        print(f"❌ Startup event logging failed: {e}")
        raise

def test_main_module():
    """Test importing the main module."""
    print("Testing main module import...")
    
    try:
        # Import main module
        import main
        print("✓ Main module imported successfully")
        
        # Check if FastAPI app exists
        if hasattr(main, 'app'):
            print("✓ FastAPI app found")
            print(f"✓ App title: {main.app.title}")
        else:
            print("⚠️ FastAPI app not found")
        
        return "Main module import successful"
    except Exception as e:
        print(f"❌ Main module import failed: {e}")
        raise

def test_enhanced_startup():
    """Test the enhanced startup process."""
    print("Testing enhanced startup process...")
    
    try:
        from main import startup_init
        
        print("Running startup_init()...")
        start_time = time.time()
        
        startup_init()
        
        elapsed = time.time() - start_time
        print(f"✓ Startup process completed in {elapsed:.2f}s")
        
        return f"Enhanced startup completed in {elapsed:.2f}s"
    except Exception as e:
        print(f"❌ Enhanced startup failed: {e}")
        raise

def main():
    """Run all tests."""
    tests = [
        ("Import Standard Libraries", test_imports),
        ("Import Database Module", test_database_module), 
        ("Create DatabaseManager", test_database_manager_creation),
        ("Test Database Connection", test_database_connection),
        ("Initialize Tables", test_table_initialization),
        ("Test User Action Logging", test_user_action_logging),
        ("Test SQL Operation Logging", test_sql_operation_logging),
        ("Test Startup Event Logging", test_startup_event_logging),
        ("Import Main Module", test_main_module),
        ("Test Enhanced Startup", test_enhanced_startup),
    ]
    
    results = []
    total_start = time.time()
    
    for test_name, test_func in tests:
        success, result = test_step(test_name, test_func)
        results.append((test_name, success, result))
        
        if not success:
            print("🛑 STOPPING TESTS due to failure")
            break
        
        # Add a small delay between tests
        time.sleep(0.5)
    
    total_elapsed = time.time() - total_start
    
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total execution time: {total_elapsed:.2f}s")
    print()
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, result in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result and success:
            print(f"        → {result}")
    
    print()
    print(f"RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
