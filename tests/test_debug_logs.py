#!/usr/bin/env python3

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db_manager
from log_utils import LogLevel, LogCategory

print("🔍 Debug Log Investigation")
print("=" * 50)

# Check if debug log table exists
print("1. Checking if debug log table exists...")
try:
    tables = db_manager.execute_query("SELECT name FROM sys.tables WHERE name LIKE ?", ("RCI_%",))
    table_names = [t['name'] for t in tables]
    print(f"   Found tables: {table_names}")
    
    if 'RCI_debug_log' in table_names:
        print("   ✅ RCI_debug_log table exists")
    else:
        print("   ❌ RCI_debug_log table NOT found")
        
except Exception as e:
    print(f"   ❌ Error checking tables: {e}")

# Test writing a log message
print("\n2. Testing log write...")
try:
    db_manager.log_debug("Test debug message from investigation", LogLevel.INFO, LogCategory.GENERAL, device_id="test_device")
    print("   ✅ Log write command completed")
except Exception as e:
    print(f"   ❌ Error writing log: {e}")

# Check how many logs exist
print("\n3. Checking log count...")
try:
    logs = db_manager.execute_query("SELECT TOP 10 * FROM RCI_debug_log ORDER BY id DESC")
    print(f"   Found {len(logs)} total logs in debug table")
    
    if logs:
        print("   Recent logs:")
        for log in logs[:3]:
            print(f"     - {log.get('timestamp', 'N/A')}: {log.get('message', 'N/A')}")
    
except Exception as e:
    print(f"   ❌ Error reading logs: {e}")

# Check if logging is configured properly
print("\n4. Checking logging configuration...")
print(f"   Log level: {db_manager.log_level}")
print(f"   Log categories: {db_manager.log_categories}")
print(f"   Should log INFO/GENERAL: {db_manager._should_log(LogLevel.INFO, LogCategory.GENERAL)}")

print("\n🏁 Investigation complete")
