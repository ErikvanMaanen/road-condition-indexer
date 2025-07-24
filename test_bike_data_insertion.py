#!/usr/bin/env python3

from database import db_manager

print("🔍 Testing Bike Data Insertion")
print("=" * 50)

# Test inserting bike data
print("1. Testing bike data insertion...")
try:
    bike_data_id = db_manager.insert_bike_data(
        latitude=52.3676,
        longitude=4.9041,
        speed=25.0,
        direction=180.0,
        roughness=2.45,
        distance_m=150.0,
        device_id="test_bike_data_insertion",
        ip_address="192.168.1.100"
    )
    print(f"   ✅ Successfully inserted bike data with ID: {bike_data_id}")
    
    # Verify it was inserted
    logs = db_manager.execute_query(f"SELECT TOP 5 * FROM RCI_bike_data WHERE device_id = ?", ("test_bike_data_insertion",))
    print(f"   ✅ Verification: Found {len(logs)} records for test device")
    
    if logs:
        record = logs[0]
        print(f"   📊 Record details: ID={record.get('id')}, lat={record.get('latitude')}, lon={record.get('longitude')}, roughness={record.get('roughness')}")
    
except Exception as e:
    print(f"   ❌ Error inserting bike data: {e}")
    import traceback
    traceback.print_exc()

print("\n🏁 Bike data insertion test complete")
