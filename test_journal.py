#!/usr/bin/env python3
"""Test script to check for SQLite journal file cycling issues."""

import time
import os
from pathlib import Path
from database import DatabaseManager, LogLevel, LogCategory

def monitor_journal_files():
    """Monitor the creation/deletion of journal files."""
    base_dir = Path(__file__).parent
    print(f"Monitoring database files in: {base_dir}")
    
    # List of journal file patterns to watch
    journal_patterns = ["*.db-journal", "*.db-wal", "*.db-shm"]
    
    print("Initial database files:")
    for pattern in journal_patterns:
        files = list(base_dir.glob(pattern))
        print(f"  {pattern}: {files}")
    
    print("\nTesting database operations...")
    
    # Create database manager with enhanced logging
    db = DatabaseManager(log_level=LogLevel.INFO)
    
    # Perform some database operations
    print("1. Initializing tables...")
    db.init_tables()
    
    print("2. Inserting test data...")
    for i in range(5):
        db.insert_bike_data(
            latitude=40.7128 + i * 0.001,
            longitude=-74.0060 + i * 0.001,
            speed=10.0 + i,
            direction=0.0,
            roughness=0.5 + i * 0.1,
            distance_m=100.0 + i * 10,
            device_id=f"test_device_{i}",
            ip_address="127.0.0.1"
        )
    
    print("3. Reading data...")
    logs, avg_roughness = db.get_logs(limit=5)
    print(f"   Retrieved {len(logs)} logs, avg roughness: {avg_roughness}")
    
    print("4. Testing debug logging...")
    for i in range(3):
        db.log_debug(f"Test log message {i}", LogLevel.INFO, LogCategory.GENERAL)
    
    debug_logs = db.get_debug_logs(limit=5)
    print(f"   Retrieved {len(debug_logs)} debug logs")
    
    print("\nDatabase operations completed. Checking for journal files...")
    
    # Check for journal files after operations
    for pattern in journal_patterns:
        files = list(base_dir.glob(pattern))
        print(f"  {pattern}: {files}")
    
    print("\nWaiting 2 seconds to see if journal files persist...")
    time.sleep(2)
    
    # Final check
    print("Final check for journal files:")
    for pattern in journal_patterns:
        files = list(base_dir.glob(pattern))
        print(f"  {pattern}: {files}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    monitor_journal_files()
