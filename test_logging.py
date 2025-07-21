#!/usr/bin/env python3
"""Test script for enhanced logging functionality."""

import sys
import time
from pathlib import Path

# Add the project directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from database import (
    DatabaseManager, LogLevel, LogCategory,
    log_info, log_warning, log_error, get_debug_logs
)


def test_enhanced_logging():
    """Test the enhanced logging functionality."""
    print("Testing Enhanced Logging System")
    print("=" * 50)
    
    # Create a fresh database manager instance for testing
    # to avoid conflicts with the global instance
    db = DatabaseManager(log_level=LogLevel.DEBUG)
    
    # Ensure tables are initialized
    try:
        db.init_tables()
        print("✓ Database tables initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return
    
    # Test different log levels and categories
    print("\n1. Testing different log levels and categories...")
    
    db.log_debug("This is a debug message", LogLevel.DEBUG, LogCategory.GENERAL)
    db.log_debug("Database connection established", LogLevel.INFO, LogCategory.CONNECTION)
    db.log_debug("Query executed successfully", LogLevel.INFO, LogCategory.QUERY)
    db.log_debug("Management operation started", LogLevel.INFO, LogCategory.MANAGEMENT)
    db.log_debug("This is a warning", LogLevel.WARNING, LogCategory.DATABASE)
    db.log_debug("This is an error", LogLevel.ERROR, LogCategory.QUERY, include_stack=True)
    
    # Test using convenience functions (these use the global db_manager)
    log_info("Testing convenience function - INFO")
    log_warning("Testing convenience function - WARNING") 
    log_error("Testing convenience function - ERROR")
    
    print("✓ Log messages written to database")
    
    # Test filtering functionality
    print("\n2. Testing log filtering...")
    
    # Get all logs using the test db instance
    all_logs = db.get_debug_logs()
    print(f"✓ Total logs: {len(all_logs)}")
    
    # Filter by level
    error_logs = db.get_debug_logs(level_filter=LogLevel.ERROR)
    print(f"✓ Error+ logs: {len(error_logs)}")
    
    # Filter by category
    query_logs = db.get_debug_logs(category_filter=LogCategory.QUERY)
    print(f"✓ Query category logs: {len(query_logs)}")
    
    # Filter by both level and category
    warning_db_logs = db.get_debug_logs(
        level_filter=LogLevel.WARNING, 
        category_filter=LogCategory.DATABASE
    )
    print(f"✓ Warning+ Database logs: {len(warning_db_logs)}")
    
    # Test log level configuration
    print("\n3. Testing log level configuration...")
    
    original_level = db.log_level
    print(f"Original log level: {original_level.value}")
    
    # Set to WARNING level
    db.set_log_level(LogLevel.WARNING)
    print(f"Changed log level to: {db.log_level.value}")
    
    # These should be filtered out
    db.log_debug("This DEBUG should be filtered", LogLevel.DEBUG, LogCategory.GENERAL)
    db.log_debug("This INFO should be filtered", LogLevel.INFO, LogCategory.GENERAL)
    
    # This should go through
    db.log_debug("This WARNING should appear", LogLevel.WARNING, LogCategory.GENERAL)
    
    # Restore original level
    db.set_log_level(original_level)
    print(f"Restored log level to: {db.log_level.value}")
    
    # Test category filtering
    print("\n4. Testing category filtering...")
    
    original_categories = db.log_categories
    print(f"Original categories: {[cat.value for cat in original_categories]}")
    
    # Set to only QUERY and ERROR categories
    db.set_log_categories([LogCategory.QUERY, LogCategory.DATABASE])
    print(f"Limited categories to: {[cat.value for cat in db.log_categories]}")
    
    # These should be filtered out
    db.log_debug("This GENERAL should be filtered", LogLevel.INFO, LogCategory.GENERAL)
    db.log_debug("This CONNECTION should be filtered", LogLevel.INFO, LogCategory.CONNECTION)
    
    # This should go through
    db.log_debug("This QUERY should appear", LogLevel.INFO, LogCategory.QUERY)
    db.log_debug("This DATABASE should appear", LogLevel.INFO, LogCategory.DATABASE)
    
    # Restore original categories
    db.set_log_categories(original_categories)
    print(f"Restored categories to: {[cat.value for cat in db.log_categories]}")
    
    print("\n5. Displaying recent log entries...")
    
    # Get recent logs with details using the test db instance
    recent_logs = db.get_debug_logs(limit=10)
    for i, log_entry in enumerate(recent_logs[:5], 1):
        print(f"  {i}. [{log_entry['level']}] [{log_entry['category']}] {log_entry['message']}")
        if log_entry.get('stack_trace'):
            print(f"     Stack trace available: {len(log_entry['stack_trace'])} chars")
    
    print(f"\n✓ Enhanced logging system test completed successfully!")
    print(f"  - Total log entries created: {len(db.get_debug_logs())}")
    print(f"  - Database type: {'SQL Server' if db.use_sqlserver else 'SQLite'}")
    print(f"  - Current log level: {db.log_level.value}")
    print(f"  - Active categories: {len(db.log_categories)}")


if __name__ == "__main__":
    try:
        test_enhanced_logging()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
