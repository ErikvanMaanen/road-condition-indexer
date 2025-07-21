#!/usr/bin/env python3
"""Simple test for basic enhanced logging functionality."""

import sys
from pathlib import Path

# Add the project directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def simple_test():
    print("Starting simple logging test...")
    
    # Test basic imports
    try:
        from database import DatabaseManager, LogLevel, LogCategory
        print("✓ Basic imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test database manager creation
    try:
        db = DatabaseManager(log_level=LogLevel.INFO)
        print("✓ DatabaseManager created")
    except Exception as e:
        print(f"❌ DatabaseManager creation failed: {e}")
        return False
    
    # Test basic logging
    try:
        db.log_debug("Test message", LogLevel.INFO, LogCategory.GENERAL)
        print("✓ Basic logging successful")
    except Exception as e:
        print(f"❌ Basic logging failed: {e}")
        return False
    
    # Test convenience functions
    try:
        from database import log_info
        log_info("Test convenience function")
        print("✓ Convenience function successful")
    except Exception as e:
        print(f"❌ Convenience function failed: {e}")
        return False
    
    # Test log retrieval
    try:
        from database import get_debug_logs
        logs = get_debug_logs(limit=5)
        print(f"✓ Log retrieval successful - found {len(logs)} logs")
    except Exception as e:
        print(f"❌ Log retrieval failed: {e}")
        return False
    
    print("✅ All basic tests passed!")
    return True

if __name__ == "__main__":
    success = simple_test()
    sys.exit(0 if success else 1)
