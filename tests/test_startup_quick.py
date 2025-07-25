#!/usr/bin/env python3
"""
Quick startup test - optimized version.
"""

import sys
import os
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("🚀 QUICK STARTUP TEST")
    print("=" * 40)
    
    start_time = time.time()
    
    try:
        print("📥 Importing main module...")
        import_start = time.time()
        from main import startup_init
        import_time = time.time() - import_start
        print(f"   ✅ Import completed in {import_time:.2f}s")
        
        print("🔧 Running startup_init()...")
        startup_start = time.time()
        startup_init()
        startup_time = time.time() - startup_start
        print(f"   ✅ Startup completed in {startup_time:.2f}s")
        
        total_time = time.time() - start_time
        print(f"\n🎉 TOTAL TIME: {total_time:.2f}s")
        print(f"   - Import: {import_time:.2f}s")
        print(f"   - Startup: {startup_time:.2f}s")
        
        # Test basic functionality
        print("\n🧪 Testing basic functionality...")
        from database import db_manager
        
        # Quick database test
        test_start = time.time()
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM RCI_bike_data")
        count = cursor.fetchone()[0]
        conn.close()
        test_time = time.time() - test_start
        
        print(f"   ✅ Database query test: {test_time:.3f}s ({count} records)")
        
        if total_time < 10:
            print("✅ PERFORMANCE: GOOD")
        elif total_time < 20:
            print("⚠️ PERFORMANCE: ACCEPTABLE")
        else:
            print("❌ PERFORMANCE: NEEDS IMPROVEMENT")
            
    except Exception as e:
        total_time = time.time() - start_time
        print(f"❌ FAILED after {total_time:.2f}s: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
