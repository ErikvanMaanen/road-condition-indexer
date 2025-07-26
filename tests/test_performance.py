#!/usr/bin/env python3
"""
Performance analysis for the startup process.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
import statistics
from typing import Optional, List, Dict, Any

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import DatabaseManager
from log_utils import LogLevel

def time_function(func_name, func):
    """Time a function and return result."""
    print(f"⏱️  Timing: {func_name}")
    start_time = time.time()
    result = func()
    elapsed = time.time() - start_time
    print(f"   ✅ {func_name}: {elapsed:.2f}s")
    return result, elapsed

def measure_database_operations() -> Dict[str, Any]:
    """Measure database operation performance."""
    print("⚡ Database Performance Test")
    
    results: Dict[str, Any] = {
        "connection_times": [],
        "query_times": [],
        "insert_times": [],
        "total_operations": 0,
        "errors": []
    }
    
    try:
        db_manager: Optional[DatabaseManager] = None
        db_manager = DatabaseManager(log_level=LogLevel.ERROR)  # Minimal logging
        
        if db_manager is None:
            raise Exception("Failed to create DatabaseManager")
        
        # Test connection performance
        print("📊 Testing connection performance...")
        for i in range(10):
            start_time = time.time()
            connection = db_manager.get_connection()
            connection.close()
            connection_time = (time.time() - start_time) * 1000
            results["connection_times"].append(connection_time)
            results["total_operations"] += 1
        
        # Test query performance
        print("📊 Testing query performance...")
        for i in range(10):
            start_time = time.time()
            result = db_manager.execute_query("SELECT 1")
            query_time = (time.time() - start_time) * 1000
            results["query_times"].append(query_time)
            results["total_operations"] += 1
        
        # Test insert performance
        print("📊 Testing insert performance...")
        test_device_id = f"perf_test_{int(time.time())}"
        
        for i in range(5):
            start_time = time.time()
            bike_data_id = db_manager.insert_bike_data(
                latitude=52.0 + (i * 0.001),
                longitude=5.0 + (i * 0.001),
                speed=20.0,
                direction=90.0,
                roughness=1.5,
                distance_m=100.0,
                device_id=test_device_id,
                ip_address="127.0.0.1"
            )
            insert_time = (time.time() - start_time) * 1000
            results["insert_times"].append(insert_time)
            results["total_operations"] += 1
        
        # Cleanup test data
        db_manager.execute_non_query(
            f"DELETE FROM RCI_bike_data WHERE device_id = ?",
            (test_device_id,)
        )
        
        # Calculate statistics
        if results["connection_times"]:
            results["connection_stats"] = {
                "avg": statistics.mean(results["connection_times"]),
                "min": min(results["connection_times"]),
                "max": max(results["connection_times"]),
                "median": statistics.median(results["connection_times"])
            }
        
        if results["query_times"]:
            results["query_stats"] = {
                "avg": statistics.mean(results["query_times"]),
                "min": min(results["query_times"]),
                "max": max(results["query_times"]),
                "median": statistics.median(results["query_times"])
            }
        
        if results["insert_times"]:
            results["insert_stats"] = {
                "avg": statistics.mean(results["insert_times"]),
                "min": min(results["insert_times"]),
                "max": max(results["insert_times"]),
                "median": statistics.median(results["insert_times"])
            }
        
        return results
        
    except Exception as e:
        results["errors"].append(str(e))
        print(f"❌ Performance test failed: {e}")
        return results

def print_performance_results(results: Dict[str, Any]) -> None:
    """Print performance test results."""
    print("\n📊 Performance Test Results")
    print("=" * 40)
    
    if results["errors"]:
        print("❌ Errors occurred during testing:")
        for error in results["errors"]:
            print(f"   {error}")
        return
    
    print(f"Total Operations: {results['total_operations']}")
    
    if "connection_stats" in results:
        stats = results["connection_stats"]
        print(f"\n🔗 Connection Performance:")
        print(f"   Average: {stats['avg']:.2f}ms")
        print(f"   Min/Max: {stats['min']:.2f}ms / {stats['max']:.2f}ms")
        print(f"   Median: {stats['median']:.2f}ms")
    
    if "query_stats" in results:
        stats = results["query_stats"]
        print(f"\n📋 Query Performance:")
        print(f"   Average: {stats['avg']:.2f}ms")
        print(f"   Min/Max: {stats['min']:.2f}ms / {stats['max']:.2f}ms")
        print(f"   Median: {stats['median']:.2f}ms")
    
    if "insert_stats" in results:
        stats = results["insert_stats"]
        print(f"\n📝 Insert Performance:")
        print(f"   Average: {stats['avg']:.2f}ms")
        print(f"   Min/Max: {stats['min']:.2f}ms / {stats['max']:.2f}ms")
        print(f"   Median: {stats['median']:.2f}ms")

def main() -> bool:
    """Run performance tests."""
    results = measure_database_operations()
    print_performance_results(results)
    
    # Return success if no errors
    return len(results["errors"]) == 0

if __name__ == "__main__":
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
    
    results = measure_database_operations()
    print_performance_results(results)
    
    print("\n✅ Performance analysis completed!")

if __name__ == "__main__":
    main()
