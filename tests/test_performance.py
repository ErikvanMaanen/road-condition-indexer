#!/usr/bin/env python3
"""
Performance analysis for the startup process.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def time_function(func_name, func):
    """Time a function and return result."""
    print(f"⏱️  Timing: {func_name}")
    start_time = time.time()
    result = func()
    elapsed = time.time() - start_time
    print(f"   ✅ {func_name}: {elapsed:.2f}s")
    return result, elapsed

def main():
    print("🔧 PERFORMANCE ANALYSIS - Startup Process")
    print("=" * 60)
    
    # Import database module
    def import_db():
        from database import DatabaseManager
        return DatabaseManager
    
    DatabaseManager, _ = time_function("Import DatabaseManager", import_db)
    
    # Create database manager
    def create_manager():
        return DatabaseManager()
    
    db_manager, _ = time_function("Create DatabaseManager instance", create_manager)
    
    # Test individual database operations
    def test_connection():
        conn = db_manager.get_connection()
        conn.close()
        return "Connection test completed"
    
    time_function("Database connection test", test_connection)
    
    # Test table initialization with detailed timing
    def test_table_init():
        print("    🔍 Breaking down table initialization:")
        
        start_total = time.time()
        
        # Database exists check
        start_step = time.time()
        db_manager.ensure_database_exists()
        print(f"      - Database exists check: {time.time() - start_step:.2f}s")
        
        # Connection
        start_step = time.time()
        conn = db_manager.get_connection()
        print(f"      - Get connection: {time.time() - start_step:.2f}s")
        
        # Table creation
        start_step = time.time()
        cursor = conn.cursor()
        db_manager._create_sqlite_tables(cursor)
        print(f"      - Create tables: {time.time() - start_step:.2f}s")
        
        # Commit
        start_step = time.time()
        conn.commit()
        print(f"      - Commit: {time.time() - start_step:.2f}s")
        
        conn.close()
        
        total_time = time.time() - start_total
        print(f"      - Total init time: {total_time:.2f}s")
        
        return f"Table init completed in {total_time:.2f}s"
    
    time_function("Table initialization breakdown", test_table_init)
    
    # Test logging operations
    def test_logging_performance():
        print("    🔍 Testing logging performance:")
        
        # Single log entry
        start_step = time.time()
        db_manager.log_debug("Test message", device_id="test_device")
        print(f"      - Single debug log: {time.time() - start_step:.2f}s")
        
        # User action log
        start_step = time.time()
        db_manager.log_user_action("TEST", "Test action", user_ip="127.0.0.1")
        print(f"      - User action log: {time.time() - start_step:.2f}s")
        
        # SQL operation log
        start_step = time.time()
        db_manager.log_sql_operation("SELECT", "SELECT 1", result_count=1, execution_time_ms=1.0)
        print(f"      - SQL operation log: {time.time() - start_step:.2f}s")
        
        # Startup event log
        start_step = time.time()
        db_manager.log_startup_event("TEST", "Test startup event")
        print(f"      - Startup event log: {time.time() - start_step:.2f}s")
        
        return "Logging performance test completed"
    
    time_function("Logging performance test", test_logging_performance)
    
    # Test multiple rapid inserts
    def test_rapid_inserts():
        print("    🔍 Testing rapid inserts:")
        start_time = time.time()
        
        for i in range(10):
            db_manager.log_debug(f"Rapid test message {i}", device_id=f"device_{i}")
        
        elapsed = time.time() - start_time
        print(f"      - 10 rapid inserts: {elapsed:.2f}s ({elapsed/10:.3f}s per insert)")
        
        return f"Rapid inserts: {elapsed:.2f}s total"
    
    time_function("Rapid insert test", test_rapid_inserts)
    
    # Test the actual startup function
    def test_startup_function():
        print("    🔍 Testing actual startup function:")
        from main import startup_init
        return startup_init()
    
    time_function("Actual startup_init() function", test_startup_function)
    
    print("\n✅ Performance analysis completed!")

if __name__ == "__main__":
    main()
