#!/usr/bin/env python3
"""
Test script to check FastAPI startup issues in the Road Condition Indexer
"""
import sys
import traceback
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test all the imports from main.py"""
    print("🔍 Testing imports...")
    
    try:
        import os
        print("✅ os imported")
        
        from pathlib import Path
        print("✅ pathlib imported")
        
        from datetime import datetime
        print("✅ datetime imported")
        
        import math
        print("✅ math imported")
        
        import re
        print("✅ re imported")
        
        import hashlib
        print("✅ hashlib imported")
        
        import pytz
        print("✅ pytz imported")
        
        from scipy import signal
        print("✅ scipy.signal imported")
        
        import requests
        print("✅ requests imported")
        
        from fastapi import FastAPI, HTTPException, Request, Depends, Query
        print("✅ FastAPI imported")
        
        from fastapi.staticfiles import StaticFiles
        print("✅ FastAPI StaticFiles imported")
        
        from fastapi.responses import FileResponse, Response, RedirectResponse
        print("✅ FastAPI responses imported")
        
        from pydantic import BaseModel, Field
        print("✅ pydantic imported")
        
        import numpy as np
        print("✅ numpy imported")
        
        from typing import Dict, List, Optional, Tuple
        print("✅ typing imported")
        
        print("🎉 All basic imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_database_import():
    """Test database module import"""
    print("\n🔍 Testing database imports...")
    
    try:
        from database import (
            DatabaseManager, TABLE_BIKE_DATA, TABLE_DEBUG_LOG, TABLE_DEVICE_NICKNAMES, TABLE_ARCHIVE_LOGS,
            TABLE_USER_ACTIONS, LogLevel, LogCategory, log_info, log_warning, log_error
        )
        print("✅ Database module imported successfully")
        
        from database import db_manager
        print("✅ Database manager instance imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Database import error: {e}")
        traceback.print_exc()
        return False

def test_azure_imports():
    """Test optional Azure imports"""
    print("\n🔍 Testing Azure imports...")
    
    try:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.web import WebSiteManagementClient
        from azure.mgmt.sql import SqlManagementClient
        from azure.mgmt.sql.models import DatabaseUpdate, Sku
        print("✅ Azure modules imported successfully")
        return True
        
    except Exception as e:
        print(f"⚠️ Azure import error (this is optional): {e}")
        return False

def test_fastapi_app_creation():
    """Test FastAPI app creation"""
    print("\n🔍 Testing FastAPI app creation...")
    
    try:
        from fastapi import FastAPI
        from fastapi.staticfiles import StaticFiles
        from pathlib import Path
        
        # Simulate the app creation from main.py
        BASE_DIR = Path(__file__).resolve().parent
        app = FastAPI(title="Road Condition Indexer")
        
        # Check if static directory exists
        static_dir = BASE_DIR / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
            print("✅ Static files mounted successfully")
        else:
            print(f"⚠️ Static directory not found at {static_dir}")
        
        print("✅ FastAPI app created successfully")
        return True
        
    except Exception as e:
        print(f"❌ FastAPI app creation error: {e}")
        traceback.print_exc()
        return False

def test_startup_function():
    """Test the startup function logic"""
    print("\n🔍 Testing startup function logic...")
    
    try:
        # Import necessary modules
        from database import db_manager, LogCategory
        from log_utils import log_info, log_error
        import time
        
        print("Starting simulated startup test...")
        
        # Test database connectivity
        print("Testing database connectivity...")
        test_result = db_manager.execute_scalar("SELECT 1")
        print(f"✅ Database test query result: {test_result}")
        
        # Test table initialization
        print("Testing table initialization...")
        db_manager.init_tables()
        print("✅ Tables initialized successfully")
        
        print("✅ Startup function logic test passed")
        return True
        
    except Exception as e:
        print(f"❌ Startup function test error: {e}")
        traceback.print_exc()
        return False

def diagnostic_startup_test() -> Dict[str, Any]:
    """Comprehensive diagnostic startup test."""
    print("🔍 Diagnostic Startup Test")
    print("=" * 40)
    
    diagnostics: Dict[str, Any] = {
        "start_time": time.time(),
        "phases": [],
        "errors": [],
        "warnings": []
    }
    
    # Phase 1: Environment Check
    print("Phase 1: Environment Check")
    env_vars = ["AZURE_SQL_SERVER", "AZURE_SQL_DATABASE", "AZURE_SQL_USER", "AZURE_SQL_PASSWORD"]
    env_status: Dict[str, Optional[str]] = {}
    
    for var in env_vars:
        value = os.getenv(var)
        env_status[var] = "***" if var == "AZURE_SQL_PASSWORD" and value else value
        status = "✅" if value else "❌"
        print(f"  {status} {var}: {env_status[var]}")
    
    diagnostics["phases"].append({
        "name": "Environment Check",
        "duration_ms": 0,
        "env_vars": env_status
    })
    
    # Phase 2: DatabaseManager Creation
    print("\nPhase 2: DatabaseManager Creation")
    phase_start = time.time()
    
    try:
        db_manager: Optional[DatabaseManager] = None
        db_manager = DatabaseManager(log_level=LogLevel.DEBUG)
        
        if db_manager is None:
            raise Exception("DatabaseManager creation returned None")
            
        phase_duration = (time.time() - phase_start) * 1000
        print(f"  ✅ DatabaseManager created in {phase_duration:.2f}ms")
        
        diagnostics["phases"].append({
            "name": "DatabaseManager Creation",
            "duration_ms": phase_duration,
            "success": True,
            "use_sqlserver": db_manager.use_sqlserver
        })
        
    except Exception as e:
        phase_duration = (time.time() - phase_start) * 1000
        print(f"  ❌ DatabaseManager creation failed: {e}")
        diagnostics["errors"].append(f"DatabaseManager creation: {e}")
        diagnostics["phases"].append({
            "name": "DatabaseManager Creation",
            "duration_ms": phase_duration,
            "success": False,
            "error": str(e)
        })
        return diagnostics
    
    # Phase 3: Table Initialization
    print("\nPhase 3: Table Initialization")
    phase_start = time.time()
    
    try:
        db_manager.init_tables()
        phase_duration = (time.time() - phase_start) * 1000
        print(f"  ✅ Tables initialized in {phase_duration:.2f}ms")
        
        diagnostics["phases"].append({
            "name": "Table Initialization",
            "duration_ms": phase_duration,
            "success": True
        })
        
    except Exception as e:
        phase_duration = (time.time() - phase_start) * 1000
        print(f"  ❌ Table initialization failed: {e}")
        diagnostics["errors"].append(f"Table initialization: {e}")
        diagnostics["phases"].append({
            "name": "Table Initialization",
            "duration_ms": phase_duration,
            "success": False,
            "error": str(e)
        })
    
    # Phase 4: Database Operations Test
    print("\nPhase 4: Database Operations Test")
    phase_start = time.time()
    
    try:
        # Test basic query and table existence
        if db_manager.use_sqlserver:
            tables_query = "SELECT name FROM sys.tables WHERE name LIKE 'RCI_%'"
        else:
            tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'RCI_%'"
        
        tables_result = db_manager.execute_query(tables_query)
        tables = [row['name'] for row in tables_result]
        
        # Test row counts
        table_counts = {}
        for table in [TABLE_BIKE_DATA, TABLE_DEBUG_LOG]:
            if table in tables:
                count = db_manager.execute_scalar(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = count if count else 0
        
        phase_duration = (time.time() - phase_start) * 1000
        print(f"  ✅ Database operations test completed in {phase_duration:.2f}ms")
        print(f"  📊 Found {len(tables)} tables: {tables}")
        print(f"  📊 Table counts: {table_counts}")
        
        diagnostics["phases"].append({
            "name": "Database Operations Test",
            "duration_ms": phase_duration,
            "success": True,
            "tables_found": tables,
            "table_counts": table_counts
        })
        
    except Exception as e:
        phase_duration = (time.time() - phase_start) * 1000
        print(f"  ❌ Database operations test failed: {e}")
        diagnostics["errors"].append(f"Database operations: {e}")
        diagnostics["phases"].append({
            "name": "Database Operations Test",
            "duration_ms": phase_duration,
            "success": False,
            "error": str(e)
        })
    
    # Summary
    total_duration = (time.time() - diagnostics["start_time"]) * 1000
    successful_phases = sum(1 for phase in diagnostics["phases"] if phase.get("success", False))
    total_phases = len(diagnostics["phases"])
    
    diagnostics.update({
        "total_duration_ms": total_duration,
        "successful_phases": successful_phases,
        "total_phases": total_phases,
        "success_rate": successful_phases / total_phases if total_phases > 0 else 0,
        "overall_success": len(diagnostics["errors"]) == 0
    })
    
    print(f"\n📊 Diagnostic Summary:")
    print(f"   Total Duration: {total_duration:.2f}ms")
    print(f"   Successful Phases: {successful_phases}/{total_phases}")
    print(f"   Errors: {len(diagnostics['errors'])}")
    print(f"   Warnings: {len(diagnostics['warnings'])}")
    
    return diagnostics

def main():
    """Main test function"""
    print("🚀 Road Condition Indexer - FastAPI Startup Diagnostic\n")
    
    tests = [
        ("Basic imports", test_imports),
        ("Database imports", test_database_import),
        ("Azure imports", test_azure_imports),
        ("FastAPI app creation", test_fastapi_app_creation),
        ("Startup function", test_startup_function),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! FastAPI startup should work correctly.")
    else:
        print("⚠️ Some tests failed. Check the errors above for details.")

if __name__ == "__main__":
    diagnostics = diagnostic_startup_test()
    exit_code = 0 if diagnostics["overall_success"] else 1
    print(f"\nDiagnostic test completed with exit code: {exit_code}")
    sys.exit(exit_code)
