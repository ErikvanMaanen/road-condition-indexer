#!/usr/bin/env python3
"""Test script to verify SQL Server enforcement.

This script tests that the application properly enforces Azure SQL Server configuration
and fails fast when required environment variables are missing.
"""

import os
import sys
import tempfile
from pathlib import Path

def test_sql_enforcement():
    """Test that the application fails when SQL Server variables are missing."""
    print("🧪 Testing SQL Server enforcement...")
    
    # Save current environment variables
    saved_env = {}
    sql_vars = [
        "AZURE_SQL_SERVER",
        "AZURE_SQL_PORT", 
        "AZURE_SQL_USER",
        "AZURE_SQL_PASSWORD",
        "AZURE_SQL_DATABASE",
    ]
    
    for var in sql_vars:
        saved_env[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    try:
        # Try to import database module - should fail
        print("   Testing import with missing SQL Server variables...")
        
        try:
            from database import DatabaseManager
            print("   ❌ FAIL: DatabaseManager imported without SQL Server configuration")
            return False
        except RuntimeError as e:
            if "SQL Server configuration required" in str(e):
                print("   ✅ PASS: Properly rejected import without SQL Server configuration")
                print(f"      Error: {e}")
            else:
                print(f"   ❌ FAIL: Unexpected error: {e}")
                return False
        except Exception as e:
            print(f"   ❌ FAIL: Unexpected exception: {e}")
            return False
    
    finally:
        # Restore environment variables
        for var, value in saved_env.items():
            if value is not None:
                os.environ[var] = value
    
    print("   ✅ SQL Server enforcement test completed successfully")
    return True

def test_with_valid_config():
    """Test that the application works with valid SQL Server configuration."""
    print("\n🧪 Testing with valid SQL Server configuration...")
    
    # Set test environment variables
    test_env = {
        "AZURE_SQL_SERVER": "test-server.database.windows.net",
        "AZURE_SQL_PORT": "1433",
        "AZURE_SQL_USER": "test-user",
        "AZURE_SQL_PASSWORD": "test-password",
        "AZURE_SQL_DATABASE": "test-database",
    }
    
    # Save current environment
    saved_env = {}
    for var in test_env:
        saved_env[var] = os.environ.get(var)
        os.environ[var] = test_env[var]
    
    try:
        # Clear module cache to force reimport
        if 'database' in sys.modules:
            del sys.modules['database']
        
        # Try to import database module - should succeed
        print("   Testing import with valid SQL Server variables...")
        
        try:
            from database import DatabaseManager
            print("   ✅ PASS: DatabaseManager imported successfully with SQL Server configuration")
            
            # Test that it's configured for SQL Server
            db_manager = DatabaseManager()
            if db_manager.use_sqlserver:
                print("   ✅ PASS: DatabaseManager correctly configured for SQL Server")
            else:
                print("   ❌ FAIL: DatabaseManager not configured for SQL Server")
                return False
                
        except Exception as e:
            print(f"   ❌ FAIL: Failed to import with valid configuration: {e}")
            return False
    
    finally:
        # Restore environment variables
        for var, value in saved_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
        
        # Clear module cache
        if 'database' in sys.modules:
            del sys.modules['database']
    
    print("   ✅ Valid configuration test completed successfully")
    return True

def main():
    """Main test function."""
    print("🚀 SQL Server Enforcement Validation")
    print("=" * 50)
    
    test1_passed = test_sql_enforcement()
    test2_passed = test_with_valid_config()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"   Missing Config Test: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Valid Config Test: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! SQL Server enforcement is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed! SQL Server enforcement may not be working properly.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
