#!/usr/bin/env python3
"""Test database operations to identify the issue."""

from database import DatabaseManager, LogLevel, LogCategory
import traceback

try:
    print('Testing database operations...')
    db = DatabaseManager()
    print('Database manager created')
    
    # Test database initialization
    db.init_tables()
    print('Tables initialized')
    
    # Test debug logging
    db.log_debug('Test debug message', LogLevel.INFO, LogCategory.GENERAL, device_id='test_device')
    print('Debug log test completed')
    
    # Test bike data insertion
    bike_id = db.insert_bike_data(52.1, 5.1, 25.0, 90.0, 1.5, 100.0, 'test_device', '127.0.0.1')
    print(f'Bike data inserted with ID: {bike_id}')
    
    # Check if logs were inserted
    logs = db.get_debug_logs(limit=5)
    print(f'Found {len(logs)} debug logs')
    for log in logs:
        print(f'  - {log.get("timestamp", "N/A")}: {log.get("message", "N/A")}')
    
    # Check if bike data was inserted
    bike_data = db.get_logs(limit=5)
    print(f'Found {len(bike_data[0])} bike data records')
    
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()
