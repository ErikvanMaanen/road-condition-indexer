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
        from database import db_manager, LogCategory, log_info, log_error
        import time
        
        print("Starting simulated startup test...")
        
        # Test database connectivity
        print("Testing database connectivity...")
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        print(f"✅ Database test query result: {result}")
        
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
    main()
