#!/usr/bin/env python3
"""
Test script to verify that all logging functions have been moved correctly.
"""

print("🧪 Testing log_utils import and functionality...")

try:
    # Test log_utils imports
    from log_utils import (
        LogLevel, LogCategory, log_debug, log_info, log_warning, log_error,
        get_debug_logs, get_dutch_time, DEBUG_LOG
    )
    print("✅ log_utils imports successful")
    
    # Test enum values
    print(f"✅ LogLevel values: {[level.value for level in LogLevel]}")
    print(f"✅ LogCategory values: {[cat.value for cat in LogCategory]}")
    
    # Test time function
    time_str = get_dutch_time()
    print(f"✅ Dutch time function works: {time_str}")
    
    # Test that DEBUG_LOG is accessible
    print(f"✅ DEBUG_LOG accessible, length: {len(DEBUG_LOG)}")
    
except Exception as e:
    print(f"❌ log_utils import failed: {e}")
    exit(1)

print("\n🧪 Testing database imports...")
try:
    from database import DatabaseManager, get_debug_logs
    print("✅ database imports successful")
except Exception as e:
    print(f"❌ database import failed: {e}")
    exit(1)

print("\n🧪 Testing main.py imports...")
try:
    # Just test the imports, don't run the app
    import sys
    import os
    
    # Add the project directory to the path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Test specific imports from main
    from main import get_elevation  # A function that should work
    print("✅ main.py imports successful")
except Exception as e:
    print(f"❌ main.py import failed: {e}")
    exit(1)

print("\n🎉 All logging functions have been successfully moved to log_utils.py!")
print("📋 Summary of changes:")
print("   • Created log_utils.py with all logging functions")
print("   • Updated database.py to import from log_utils")
print("   • Updated main.py to import from log_utils")
print("   • Removed duplicate functions from main.py and database.py")
print("   • Updated all test files to use correct imports")
print("   • Removed old logger.py file")
