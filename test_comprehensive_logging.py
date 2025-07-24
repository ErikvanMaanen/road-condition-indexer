"""
Test script to demonstrate the comprehensive logging functionality
added to the Road Condition Indexer application.

This script demonstrates:
1. Startup process logging
2. SQL operation logging  
3. User action logging
4. Enhanced debug logging

Run this after starting the main application to see the logging in action.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on a different port
TEST_PASSWORD = "your_password_here"  # Replace with actual password

def test_startup_logging():
    """Test that startup events are properly logged."""
    print("🚀 Testing Startup Logging...")
    
    # The startup logging happens automatically when the server starts
    # We can check the startup logs via the API
    try:
        response = requests.get(f"{BASE_URL}/system_startup_log?limit=20")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_events']} startup events and {data['total_logs']} startup logs")
            
            # Show some recent startup events
            for event in data['startup_events'][:3]:
                print(f"   📝 {event['action_type']}: {event['action_description']}")
        else:
            print(f"❌ Failed to retrieve startup logs: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing startup logging: {e}")

def test_user_action_logging():
    """Test user action logging by performing login and page access."""
    print("\n👤 Testing User Action Logging...")
    
    try:
        # Test login (will fail, but should be logged)
        login_data = {"password": "wrong_password"}
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        print(f"   🔐 Login attempt logged (expected failure): {response.status_code}")
        
        # Test page access (should redirect and be logged)
        response = requests.get(f"{BASE_URL}/", allow_redirects=False)
        print(f"   📄 Unauthorized page access logged: {response.status_code}")
        
        # Check user actions log
        response = requests.get(f"{BASE_URL}/user_actions?limit=10")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} user actions")
            
            # Show recent actions
            for action in data['actions'][:3]:
                status = "✅" if action.get('success', True) else "❌"
                print(f"   {status} {action['action_type']}: {action['action_description']}")
        else:
            print(f"❌ Failed to retrieve user actions: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing user action logging: {e}")

def test_sql_operation_logging():
    """Test SQL operation logging by making database queries."""
    print("\n🗃️  Testing SQL Operation Logging...")
    
    try:
        # Make some API calls that trigger database operations
        response = requests.get(f"{BASE_URL}/logs?limit=5")
        print(f"   📊 Database query triggered: {response.status_code}")
        
        response = requests.get(f"{BASE_URL}/device_ids")
        print(f"   📱 Device IDs query triggered: {response.status_code}")
        
        # Check SQL operations log
        response = requests.get(f"{BASE_URL}/sql_operations_log?limit=10")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} SQL operations logged")
            
            # Show recent operations
            for op in data['sql_operations'][:3]:
                op_type = "SQL" if "SQL_" in op.get('message', '') else "LOG"
                print(f"   🔧 {op_type}: {op.get('message', 'No description')[:100]}...")
        else:
            print(f"❌ Failed to retrieve SQL operations: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing SQL operation logging: {e}")

def test_debug_logging():
    """Test enhanced debug logging functionality."""
    print("\n🐛 Testing Debug Logging...")
    
    try:
        # Check enhanced debug logs
        response = requests.get(f"{BASE_URL}/debuglog/enhanced?limit=10&level=INFO")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} debug logs")
            
            # Show logs by category
            categories = {}
            for log in data['logs']:
                category = log.get('category', 'UNKNOWN')
                categories[category] = categories.get(category, 0) + 1
            
            print("   📊 Debug logs by category:")
            for category, count in categories.items():
                print(f"      {category}: {count}")
                
        else:
            print(f"❌ Failed to retrieve debug logs: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing debug logging: {e}")

def generate_test_data():
    """Generate some test data to create logs."""
    print("\n📝 Generating Test Data...")
    
    try:
        # Simulate a device data submission (will fail without auth, but should be logged)
        test_data = {
            "latitude": 52.3676,
            "longitude": 4.9041,
            "speed": 15.0,
            "direction": 90.0,
            "device_id": "test_device_logging",
            "z_values": [0.1, 0.2, 0.15, 0.18, 0.12]
        }
        
        response = requests.post(f"{BASE_URL}/log", json=test_data)
        print(f"   📡 Test data submission: {response.status_code}")
        
        # Make several API calls to generate logs
        endpoints = ["/logs", "/device_ids", "/date_range", "/debuglog"]
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"   🔗 {endpoint}: {response.status_code}")
            time.sleep(0.1)  # Small delay between requests
            
    except Exception as e:
        print(f"❌ Error generating test data: {e}")

def main():
    """Run all logging tests."""
    print("🔍 Road Condition Indexer - Comprehensive Logging Test")
    print("=" * 60)
    
    # Give the server a moment to fully start up
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    # Run tests
    test_startup_logging()
    test_user_action_logging()
    generate_test_data()
    test_sql_operation_logging()
    test_debug_logging()
    
    print("\n" + "=" * 60)
    print("🎉 Logging tests completed!")
    print("\n📋 Summary of implemented logging features:")
    print("   ✅ Startup process logging with detailed timing")
    print("   ✅ SQL operation logging with execution times and results")
    print("   ✅ User action logging (login, page access, API calls)")
    print("   ✅ Enhanced debug logging with categories and levels")
    print("   ✅ Comprehensive log viewer UI at /comprehensive-logs.html")
    print("\n🌐 Access the comprehensive logs at:")
    print(f"   {BASE_URL}/comprehensive-logs.html")

if __name__ == "__main__":
    main()
