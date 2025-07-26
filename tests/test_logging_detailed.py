#!/usr/bin/env python3
"""
Detailed logging functionality tests.
"""

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from typing import Optional, List, Dict, Any
from database import DatabaseManager
from log_utils import LogLevel, LogCategory, log_info, log_warning, log_error, log_debug

def test_logging_levels() -> bool:
    """Test different logging levels."""
    print("=== Testing Logging Levels ===")
    
    try:
        db_manager: Optional[DatabaseManager] = None
        db_manager = DatabaseManager(log_level=LogLevel.DEBUG)
        
        if db_manager is None:
            print("❌ Failed to create DatabaseManager")
            return False
        
        # Test each log level
        test_message = "Test message for level testing"
        device_id: Optional[str] = "test_device_logging"
        
        log_debug(f"DEBUG: {test_message}", device_id=device_id)
        log_info(f"INFO: {test_message}", device_id=device_id)
        log_warning(f"WARNING: {test_message}", device_id=device_id)
        log_error(f"ERROR: {test_message}", device_id=device_id)
        
        # Direct database manager logging
        db_manager.log_debug("CRITICAL test message", LogLevel.CRITICAL, LogCategory.GENERAL, device_id=device_id)
        
        print("✅ All logging levels tested")
        return True
        
    except Exception as e:
        print(f"❌ Logging levels test failed: {e}")
        return False

def test_logging_categories() -> bool:
    """Test different logging categories."""
    print("\n=== Testing Logging Categories ===")
    
    try:
        db_manager = DatabaseManager(log_level=LogLevel.DEBUG)
        device_id: Optional[str] = "test_device_categories"
        
        # Test each category
        categories_to_test = [
            LogCategory.DATABASE,
            LogCategory.CONNECTION,
            LogCategory.QUERY,
            LogCategory.MANAGEMENT,
            LogCategory.GENERAL,
            LogCategory.STARTUP,
            LogCategory.USER_ACTION
        ]
        
        for category in categories_to_test:
            db_manager.log_debug(
                f"Test message for category {category.value}",
                LogLevel.INFO,
                category,
                device_id=device_id
            )
        
        print(f"✅ Tested {len(categories_to_test)} log categories")
        return True
        
    except Exception as e:
        print(f"❌ Logging categories test failed: {e}")
        return False

def test_log_filtering() -> bool:
    """Test log level and category filtering."""
    print("\n=== Testing Log Filtering ===")
    
    try:
        db_manager = DatabaseManager(log_level=LogLevel.WARNING)  # Only WARNING and above
        device_id: Optional[str] = "test_device_filtering"
        
        # These should be filtered out
        db_manager.log_debug("DEBUG message - should be filtered", LogLevel.DEBUG, LogCategory.GENERAL, device_id=device_id)
        db_manager.log_debug("INFO message - should be filtered", LogLevel.INFO, LogCategory.GENERAL, device_id=device_id)
        
        # These should be logged
        db_manager.log_debug("WARNING message - should be logged", LogLevel.WARNING, LogCategory.GENERAL, device_id=device_id)
        db_manager.log_debug("ERROR message - should be logged", LogLevel.ERROR, LogCategory.GENERAL, device_id=device_id)
        
        # Test category filtering
        db_manager.set_log_categories([LogCategory.DATABASE])  # Only DATABASE category
        
        db_manager.log_debug("DATABASE message - should be logged", LogLevel.ERROR, LogCategory.DATABASE, device_id=device_id)
        db_manager.log_debug("GENERAL message - should be filtered", LogLevel.ERROR, LogCategory.GENERAL, device_id=device_id)
        
        print("✅ Log filtering tested")
        return True
        
    except Exception as e:
        print(f"❌ Log filtering test failed: {e}")
        return False

def test_log_retrieval() -> bool:
    """Test log retrieval with filtering."""
    print("\n=== Testing Log Retrieval ===")
    
    try:
        db_manager = DatabaseManager(log_level=LogLevel.DEBUG)
        device_id: Optional[str] = "test_device_retrieval"
        
        # Insert some test logs
        test_logs = [
            (LogLevel.DEBUG, LogCategory.GENERAL, "Debug message 1"),
            (LogLevel.INFO, LogCategory.DATABASE, "Info message 1"),
            (LogLevel.WARNING, LogCategory.QUERY, "Warning message 1"),
            (LogLevel.ERROR, LogCategory.MANAGEMENT, "Error message 1"),
        ]
        
        for level, category, message in test_logs:
            db_manager.log_debug(message, level, category, device_id=device_id)
        
        # Wait a moment for logs to be written
        time.sleep(0.1)
        
        # Test retrieval with different filters
        all_logs = db_manager.get_debug_logs(limit=10)
        device_logs = db_manager.get_debug_logs(device_id_filter=device_id, limit=10)
        warning_logs = db_manager.get_debug_logs(level_filter=LogLevel.WARNING, limit=10)
        database_logs = db_manager.get_debug_logs(category_filter=LogCategory.DATABASE, limit=10)
        
        print(f"✅ Log retrieval tested:")
        print(f"   All logs: {len(all_logs)}")
        print(f"   Device logs: {len(device_logs)}")
        print(f"   Warning+ logs: {len(warning_logs)}")
        print(f"   Database logs: {len(database_logs)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Log retrieval test failed: {e}")
        return False

def run_detailed_logging_tests() -> Dict[str, Any]:
    """Run all detailed logging tests."""
    print("🔍 Detailed Logging Tests")
    print("=" * 40)
    
    tests = [
        ("Logging Levels", test_logging_levels),
        ("Logging Categories", test_logging_categories),
        ("Log Filtering", test_log_filtering),
        ("Log Retrieval", test_log_retrieval)
    ]
    
    passed = 0
    total = len(tests)
    results: Dict[str, Any] = {"tests": []}
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if success:
                passed += 1
            results["tests"].append({
                "name": test_name,
                "success": success,
                "error": None
            })
        except Exception as e:
            results["tests"].append({
                "name": test_name,
                "success": False,
                "error": str(e)
            })
            print(f"❌ {test_name} crashed: {e}")
    
    success_rate = passed / total
    results.update({
        "passed": passed,
        "total": total,
        "success_rate": success_rate,
        "overall_success": success_rate >= 0.75
    })
    
    print(f"\n📊 Detailed Logging Tests Summary: {passed}/{total} passed ({success_rate:.1%})")
    
    return results

if __name__ == "__main__":
    results = run_detailed_logging_tests()
    exit_code = 0 if results["overall_success"] else 1
    sys.exit(exit_code)
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
