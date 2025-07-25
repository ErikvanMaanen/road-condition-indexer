#!/usr/bin/env python3
"""Test the exact operations that happen in the /bike-data endpoint."""

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db_manager
from log_utils import log_info, log_error, log_debug
from datetime import datetime
import traceback

def test_bike_data_endpoint_simulation():
    """Simulate exactly what happens in the /bike-data endpoint."""
    print("=== Simulating /bike-data endpoint operations ===")
    
    # Test data similar to what would come from the app
    test_entry = {
        'latitude': 52.1073946,
        'longitude': 5.1340406,
        'speed': 24.364206504821777,
        'direction': 90.0,
        'device_id': 'test_device_endpoint',
        'z_values': [0.1, 0.2, 0.3, 0.4, 0.5] * 12,  # 60 values
        'user_agent': 'test-agent',
        'device_fp': 'test-fp',
        'record_source_data': False
    }
    
    try:
        # Simulate the main.py log_debug calls
        print("Step 1: Initial logging")
        
        log_info(f"Received log entry from device {test_entry['device_id']}", device_id=test_entry['device_id'])
        log_debug(f"Log entry details: lat={test_entry['latitude']}, lon={test_entry['longitude']}, speed={test_entry['speed']}, z_values count={len(test_entry['z_values'])}", device_id=test_entry['device_id'])
        
        print("Step 2: Computing roughness")
        from main import compute_roughness
        
        avg_speed = test_entry['speed']
        dt_sec = 2.0  # Simulate 2 second interval
        
        roughness = compute_roughness(
            test_entry['z_values'],
            avg_speed,
            dt_sec,
            freq_min=0.5,
            freq_max=50.0,
        )
        
        distance_m = 50.0  # Simulate 50m distance
        ip_address = '127.0.0.1'
        
        log_info(f"Calculated roughness: {roughness:.3f} for device {test_entry['device_id']}", device_id=test_entry['device_id'])
        
        print("Step 3: Database operations")
        log_debug(f"About to insert bike data for device {test_entry['device_id']}", device_id=test_entry['device_id'])
        
        # Insert bike data
        bike_data_id = db_manager.insert_bike_data(
            test_entry['latitude'],
            test_entry['longitude'],
            test_entry['speed'],
            test_entry['direction'],
            roughness,
            distance_m,
            test_entry['device_id'],
            ip_address
        )
        
        log_debug(f"Bike data inserted with ID {bike_data_id} for device {test_entry['device_id']}", device_id=test_entry['device_id'])
        
        # Update device info
        log_debug(f"About to upsert device info for device {test_entry['device_id']}", device_id=test_entry['device_id'])
        db_manager.upsert_device_info(test_entry['device_id'], test_entry['user_agent'], test_entry['device_fp'])
        
        log_info(f"Successfully stored data for device {test_entry['device_id']}", device_id=test_entry['device_id'])
        
        print("Step 4: Verification")
        # Check if data was actually inserted
        logs = db_manager.get_debug_logs(limit=10)
        print(f"Found {len(logs)} debug logs")
        for i, log in enumerate(logs[:5]):
            print(f"  {i+1}. {log.get('message', 'N/A')}")
        
        bike_data = db_manager.get_logs(limit=5)
        print(f"Found {len(bike_data[0])} bike data records")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bike_data_endpoint_simulation()
    print(f"\nTest result: {'PASS' if success else 'FAIL'}")
