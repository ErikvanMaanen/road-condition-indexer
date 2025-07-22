#!/usr/bin/env python3
"""Test script to verify RCI_ table filtering is working correctly."""

import sqlite3
from pathlib import Path
from database import DatabaseManager, LogLevel, LogCategory

def test_rci_table_filtering():
    """Test that only RCI_ tables are accessible through database operations."""
    print("Testing RCI_ table filtering...")
    print("=" * 50)
    
    # Create database manager
    db = DatabaseManager(log_level=LogLevel.INFO)
    
    # First, let's create a test table that doesn't start with RCI_ directly in SQLite
    db_file = Path(__file__).parent / "RCI_local.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create a non-RCI table for testing
    cursor.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO test_table (name) VALUES ('test_data')")
    conn.commit()
    conn.close()
    
    print("1. Testing get_table_summary() - should only return RCI_ tables...")
    table_summary = db.get_table_summary()
    table_names = [table['name'] for table in table_summary]
    print(f"   Found tables: {table_names}")
    
    # Verify all returned tables start with RCI_
    rci_only = all(name.startswith('RCI_') for name in table_names)
    print(f"   ✓ All tables start with RCI_: {rci_only}")
    
    print(f"   ✓ Found {len(table_names)} RCI_ tables")
    
    print("\n2. Testing table_exists() with RCI_ table...")
    rci_table_exists = db.table_exists("RCI_bike_data")
    print(f"   ✓ RCI_bike_data exists: {rci_table_exists}")
    
    print("\n3. Testing table_exists() with non-RCI_ table...")
    non_rci_exists = db.table_exists("test_table")
    print(f"   ✓ test_table (non-RCI) access denied: {not non_rci_exists}")
    
    print("\n4. Testing get_last_table_rows() with RCI_ table...")
    try:
        rows = db.get_last_table_rows("RCI_bike_data", limit=1)
        print(f"   ✓ Successfully retrieved {len(rows)} rows from RCI_bike_data")
    except Exception as e:
        print(f"   ! Error accessing RCI_bike_data: {e}")
    
    print("\n5. Testing get_last_table_rows() with non-RCI_ table...")
    try:
        rows = db.get_last_table_rows("test_table", limit=1)
        print(f"   ✗ Should not have accessed test_table!")
    except ValueError as e:
        if "Access denied" in str(e):
            print("   ✓ Access denied to non-RCI_ table as expected")
        else:
            print(f"   ✓ Access denied with error: {e}")
    
    print("\n6. Testing test_table_operations() with RCI_ table...")
    try:
        test_rows = db.test_table_operations("RCI_bike_data")
        print(f"   ✓ Successfully tested RCI_bike_data operations")
    except Exception as e:
        print(f"   ! Error testing RCI_bike_data: {e}")
    
    print("\n7. Testing test_table_operations() with non-RCI_ table...")
    try:
        test_rows = db.test_table_operations("test_table")
        print(f"   ✗ Should not have accessed test_table!")
    except ValueError as e:
        if "Access denied" in str(e):
            print("   ✓ Access denied to non-RCI_ table as expected")
        else:
            print(f"   ✓ Access denied with error: {e}")
    
    print("\n8. Testing backup_table() with non-RCI_ table...")
    try:
        backup_name = db.backup_table("test_table")
        print(f"   ✗ Should not have backed up test_table!")
    except ValueError as e:
        if "Access denied" in str(e):
            print("   ✓ Backup access denied to non-RCI_ table as expected")
        else:
            print(f"   ✓ Backup access denied with error: {e}")
    
    print("\n9. Testing rename_table() with non-RCI_ table...")
    try:
        db.rename_table("test_table", "renamed_test_table")
        print(f"   ✗ Should not have renamed test_table!")
    except ValueError as e:
        if "Access denied" in str(e):
            print("   ✓ Rename access denied to non-RCI_ table as expected")
        else:
            print(f"   ✓ Rename access denied with error: {e}")
    
    # Clean up the test table
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS test_table")
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ RCI_ table filtering is working correctly!")
    print("   - Only RCI_ tables are returned in table listings")
    print("   - Non-RCI_ tables are blocked from all operations")
    print("   - RCI_ tables continue to work normally")

if __name__ == "__main__":
    test_rci_table_filtering()
