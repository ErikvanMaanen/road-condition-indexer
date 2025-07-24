#!/usr/bin/env python3

from database import db_manager, LogLevel, LogCategory, TABLE_DEBUG_LOG

print("🔍 Detailed Debug Log Investigation")
print("=" * 50)

# Test the execute_non_query directly 
print("1. Testing execute_non_query directly...")
try:
    timestamp = db_manager._get_dutch_time()
    result = db_manager.execute_non_query(
        f"""INSERT INTO {TABLE_DEBUG_LOG} (timestamp, level, category, device_id, message, stack_trace) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (timestamp, 'INFO', 'GENERAL', 'test_device', 'Direct insert test message', None)
    )
    print(f"   ✅ Direct insert result: {result}")
    
    # Check if it's there
    logs = db_manager.execute_query("SELECT TOP 5 * FROM RCI_debug_log ORDER BY id DESC")
    print(f"   Now have {len(logs)} logs in table")
    
except Exception as e:
    print(f"   ❌ Error with direct insert: {e}")
    import traceback
    traceback.print_exc()

print("\n2. Testing log_debug with exception capture...")

# Temporarily modify the log_debug method to capture exceptions
import types

def log_debug_with_exception_capture(self, message: str, level: LogLevel = LogLevel.INFO, 
                                   category: LogCategory = LogCategory.GENERAL,
                                   include_stack: bool = False, device_id: str = None) -> None:
    """Modified log_debug that shows exceptions instead of hiding them."""
    if not self._should_log(level, category):
        print(f"   Skipped logging due to level/category filter")
        return
        
    timestamp = self._get_dutch_time()
    stack_trace = None
    
    if include_stack or level in [LogLevel.ERROR, LogLevel.CRITICAL]:
        import traceback
        stack_trace = traceback.format_stack()[-3:-1]
        stack_trace = ''.join(stack_trace).strip()
    
    try:
        print(f"   Attempting to insert: {message}")
        print(f"   Params: timestamp={timestamp}, level={level.value}, category={category.value}")
        print(f"   device_id={device_id}, stack_trace={stack_trace}")
        
        result = self.execute_non_query(
            f"""INSERT INTO {TABLE_DEBUG_LOG} (timestamp, level, category, device_id, message, stack_trace) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (timestamp, level.value, category.value, device_id, message, stack_trace)
        )
        print(f"   ✅ Insert successful, result: {result}")
    except Exception as e:
        print(f"   ❌ Exception during log insert: {e}")
        import traceback
        traceback.print_exc()

# Replace the method temporarily
db_manager.log_debug = types.MethodType(log_debug_with_exception_capture, db_manager)

# Test it
db_manager.log_debug("Test with exception capture", LogLevel.INFO, LogCategory.GENERAL, device_id="test_device_2")

print("\n🏁 Detailed investigation complete")
