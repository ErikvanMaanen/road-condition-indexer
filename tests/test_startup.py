#!/usr/bin/env python3
"""Test application startup functionality."""

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from typing import Optional, Dict, Any
from database import DatabaseManager
from log_utils import LogLevel, LogCategory

def test_database_manager_initialization() -> bool:
    """Test DatabaseManager initialization."""
    print("=== Testing DatabaseManager Initialization ===")
    
    try:
        start_time = time.time()
        db_manager: Optional[DatabaseManager] = None
        
        # Test initialization
        db_manager = DatabaseManager(log_level=LogLevel.INFO)
        
        if db_manager is None:
            print("❌ DatabaseManager initialization failed - None returned")
            return False
            
        initialization_time = (time.time() - start_time) * 1000
        print(f"✅ DatabaseManager initialized in {initialization_time:.2f}ms")
        
        # Test basic properties
        print(f"📊 Configuration:")
        print(f"   - use_sqlserver: {db_manager.use_sqlserver}")
        print(f"   - log_level: {db_manager.log_level}")
        print(f"   - log_categories count: {len(db_manager.log_categories)}")
        
        return True
        
    except Exception as e:
        print(f"❌ DatabaseManager initialization failed: {e}")
        return False

def test_table_initialization() -> bool:
    """Test database table initialization."""
    print("\n=== Testing Table Initialization ===")
    
    try:
        db_manager = DatabaseManager(log_level=LogLevel.INFO)
        
        start_time = time.time()
        db_manager.init_tables()
        table_init_time = (time.time() - start_time) * 1000
        
        print(f"✅ Tables initialized in {table_init_time:.2f}ms")
        return True
        
    except Exception as e:
        print(f"❌ Table initialization failed: {e}")
        return False

def test_database_connectivity() -> bool:
    """Test basic database connectivity."""
    print("\n=== Testing Database Connectivity ===")
    
    try:
        db_manager = DatabaseManager(log_level=LogLevel.INFO)
        
        connection: Optional[Any] = None
        connection = db_manager.get_connection()
        
        if connection is None:
            print("❌ Database connection failed - None returned")
            return False
            
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        connection.close()
        
        if result and result[0] == 1:
            print("✅ Database connectivity test passed")
            return True
        else:
            print("❌ Database connectivity test failed - unexpected result")
            return False
            
    except Exception as e:
        print(f"❌ Database connectivity test failed: {e}")
        return False

def run_startup_tests() -> Dict[str, Any]:
    """Run all startup tests."""
    print("🚀 Starting Application Startup Tests")
    print("=" * 50)
    
    tests = [
        ("DatabaseManager Initialization", test_database_manager_initialization),
        ("Table Initialization", test_table_initialization),
        ("Database Connectivity", test_database_connectivity)
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
        "overall_success": success_rate >= 0.8
    })
    
    print("\n" + "=" * 50)
    print(f"📊 Startup Tests Summary: {passed}/{total} passed ({success_rate:.1%})")
    print("=" * 50)
    
    return results

if __name__ == "__main__":
    results = run_startup_tests()
    exit_code = 0 if results["overall_success"] else 1
    sys.exit(exit_code)
