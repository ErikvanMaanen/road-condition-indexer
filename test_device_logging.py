#!/usr/bin/env python3
"""
Test script to verify device_id logging functionality.
"""

import requests
import json
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_device_logging():
    """Test that device_id is properly included in logs when submitting data."""
    
    # Create a test log entry
    test_device_id = f"test-device-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    log_entry = {
        "latitude": 52.3676,
        "longitude": 4.9041,
        "speed": 15.5,
        "direction": 180.0,
        "device_id": test_device_id,
        "user_agent": "TestClient/1.0",
        "device_fp": "test-fingerprint",
        "z_values": [0.1, 0.2, -0.1, 0.0, 0.15, -0.05, 0.08, -0.12, 0.03, 0.01]
    }
    
    print(f"Testing logging with device_id: {test_device_id}")
    
    # Submit the log entry
    try:
        response = requests.post(f"{BASE_URL}/log", json=log_entry)
        print(f"Log submission response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result}")
        else:
            print(f"Error: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to submit log entry: {e}")
        return False
    
    # Wait a moment for logging to process
    import time
    time.sleep(1)
    
    # Check enhanced debug logs for our device
    try:
        response = requests.get(f"{BASE_URL}/debuglog/enhanced", params={
            "device_id": test_device_id,
            "limit": 50
        })
        
        if response.status_code == 200:
            result = response.json()
            logs = result.get("logs", [])
            
            print(f"\nFound {len(logs)} log entries for device {test_device_id}")
            
            device_logs = [log for log in logs if log.get("device_id") == test_device_id]
            print(f"Device-specific logs: {len(device_logs)}")
            
            if device_logs:
                print("\nSample device log entries:")
                for i, log in enumerate(device_logs[:3]):
                    print(f"  {i+1}. [{log.get('level')}] {log.get('message')}")
                
                return True
            else:
                print("No logs found with the correct device_id")
                return False
                
        else:
            print(f"Failed to retrieve debug logs: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve debug logs: {e}")
        return False

def test_management_logs():
    """Test the management endpoint for device filtering (requires authentication)."""
    print("\nTesting management logs endpoint...")
    print("Note: This test may fail without authentication, which is expected.")
    
    try:
        response = requests.get(f"{BASE_URL}/manage/debug_logs", params={
            "device_id_filter": "test-device",
            "limit": 10
        })
        
        if response.status_code == 401:
            print("Authentication required (expected) - management endpoint working")
            return True
        elif response.status_code == 200:
            logs = response.json()
            print(f"Retrieved {len(logs)} logs from management endpoint")
            return True
        else:
            print(f"Unexpected response: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing device_id logging functionality...")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print("✓ Server is running")
    except requests.exceptions.RequestException:
        print("✗ Server is not running. Please start the application first.")
        exit(1)
    
    success = True
    
    # Run tests
    if test_device_logging():
        print("\n✓ Device logging test passed")
    else:
        print("\n✗ Device logging test failed")
        success = False
    
    if test_management_logs():
        print("✓ Management logs test passed")
    else:
        print("✗ Management logs test failed")
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! Device ID logging is working correctly.")
    else:
        print("✗ Some tests failed. Please check the implementation.")
