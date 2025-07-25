#!/usr/bin/env python3
"""
Simple test runner for the Road Condition Indexer.
This script runs both database-only tests and full API tests (if server is running).
"""

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess
import sys
import time
import threading
import signal
import os
from pathlib import Path

# Load .env if running locally
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def run_database_only_tests():
    """Run tests that only require database access."""
    print("🧪 Running Database-Only Tests")
    print("=" * 50)
    
    # Set environment variable to skip API tests
    env = os.environ.copy()
    env['RCI_TEST_MODE'] = 'database_only'
    
    try:
        result = subprocess.run([
            sys.executable, 'tests/test_comprehensive_data_flow.py'
        ], cwd=Path(__file__).parent.parent, env=env, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running database tests: {e}")
        return False

def start_api_server():
    """Start the FastAPI server for testing."""
    print("🚀 Starting API server...")
    try:
        process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'
        ], cwd=Path(__file__).parent.parent)
        
        # Give server time to start
        time.sleep(3)
        return process
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        return None

def run_full_tests():
    """Run all tests including API tests."""
    print("🌐 Running Full Test Suite (Database + API)")
    print("=" * 50)
    
    server_process = start_api_server()
    if not server_process:
        print("❌ Failed to start API server")
        return False
    
    try:
        # Wait a bit more for server to be ready
        time.sleep(2)
        
        # Run comprehensive tests
        result = subprocess.run([
            sys.executable, 'tests/test_comprehensive_data_flow.py'
        ], cwd=Path(__file__).parent.parent, capture_output=False)
        
        success = result.returncode == 0
    except Exception as e:
        print(f"❌ Error running full tests: {e}")
        success = False
    finally:
        # Stop the server
        print("🛑 Stopping API server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()
    
    return success

def main():
    """Main test runner."""
    print("🧪 Road Condition Indexer Test Runner")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'full':
        success = run_full_tests()
    else:
        print("💡 Running database-only tests. Use 'python test_runner.py full' for API tests.")
        print()
        success = run_database_only_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
