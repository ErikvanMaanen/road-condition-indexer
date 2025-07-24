#!/usr/bin/env python3
"""Test database operations in different contexts."""

import asyncio
from database import DatabaseManager, LogLevel, LogCategory, log_info, log_error
import traceback

def test_standalone():
    """Test database operations standalone."""
    print("=== Testing standalone database operations ===")
    try:
        db = DatabaseManager()
        db.init_tables()
        
        # Test logging
        log_info("Standalone test message", device_id="test_device")
        
        # Test bike data insertion
        bike_id = db.insert_bike_data(52.1, 5.1, 25.0, 90.0, 1.5, 100.0, 'test_device', '127.0.0.1')
        print(f"Bike data inserted with ID: {bike_id}")
        
        # Check logs
        logs = db.get_debug_logs(limit=3)
        print(f"Found {len(logs)} debug logs:")
        for log in logs:
            print(f"  - {log.get('message', 'N/A')}")
        
        # Check bike data
        bike_data = db.get_logs(limit=3)
        print(f"Found {len(bike_data[0])} bike data records")
        
        return True
    except Exception as e:
        print(f"Standalone test failed: {e}")
        traceback.print_exc()
        return False

def test_with_imported_manager():
    """Test using the imported db_manager from database module."""
    print("\n=== Testing with imported db_manager ===")
    try:
        from database import db_manager
        
        # Test logging
        log_info("Imported manager test message", device_id="test_device_2")
        
        # Test bike data insertion
        bike_id = db_manager.insert_bike_data(52.2, 5.2, 26.0, 91.0, 1.6, 101.0, 'test_device_2', '127.0.0.1')
        print(f"Bike data inserted with ID: {bike_id}")
        
        # Check logs
        logs = db_manager.get_debug_logs(limit=3)
        print(f"Found {len(logs)} debug logs:")
        for log in logs:
            print(f"  - {log.get('message', 'N/A')}")
        
        # Check bike data
        bike_data = db_manager.get_logs(limit=3)
        print(f"Found {len(bike_data[0])} bike data records")
        
        return True
    except Exception as e:
        print(f"Imported manager test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test1_ok = test_standalone()
    test2_ok = test_with_imported_manager()
    
    print(f"\nResults:")
    print(f"Standalone test: {'PASS' if test1_ok else 'FAIL'}")
    print(f"Imported manager test: {'PASS' if test2_ok else 'FAIL'}")
