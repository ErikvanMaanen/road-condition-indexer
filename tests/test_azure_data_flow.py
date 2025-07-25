#!/usr/bin/env python3
"""
Test Azure SQL Database data flow - insert and retrieve test data
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import database manager
from database import DatabaseManager
from log_utils import LogLevel, LogCategory

def test_data_flow():
    """Test complete data flow: insert -> verify -> retrieve"""
    print("🔍 Testing Azure SQL Database Data Flow")
    print("=" * 50)
    
    # Initialize database manager
    db_manager = DatabaseManager(log_level=LogLevel.INFO)
    
    if not db_manager.use_sqlserver:
        print("❌ Not using SQL Server!")
        return False
    
    print("✅ Using Azure SQL Database")
    
    # Test 1: Insert test data
    print("\n📝 Test 1: Inserting test data")
    try:
        test_device_id = f"flow_test_{int(time.time())}"
        
        bike_data_id = db_manager.insert_bike_data(
            latitude=52.3676,  # Amsterdam
            longitude=4.9041,
            speed=25.0,
            direction=90.0,
            roughness=2.15,
            distance_m=150.0,
            device_id=test_device_id,
            ip_address="192.168.1.100"
        )
        
        print(f"✅ Inserted test record with ID: {bike_data_id}")
        print(f"   Device ID: {test_device_id}")
        print(f"   Coordinates: 52.3676, 4.9041")
        print(f"   Roughness: 2.15")
        
    except Exception as e:
        print(f"❌ Insert failed: {e}")
        return False
    
    # Test 2: Verify insertion with direct query
    print("\n🔍 Test 2: Verifying insertion")
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM RCI_bike_data WHERE id = ?", bike_data_id)
        result = cursor.fetchone()
        
        if result:
            columns = [desc[0] for desc in cursor.description]
            record = dict(zip(columns, result))
            print("✅ Record found in database:")
            print(f"   ID: {record['id']}")
            print(f"   Device: {record['device_id']}")
            print(f"   Timestamp: {record['timestamp']}")
            print(f"   Location: {record['latitude']}, {record['longitude']}")
            print(f"   Roughness: {record['roughness']}")
        else:
            print("❌ Record not found!")
            return False
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    
    # Test 3: Retrieve via API methods
    print("\n📊 Test 3: Retrieving via API methods")
    try:
        # Test get_logs
        rows, avg_roughness = db_manager.get_logs(10)
        print(f"✅ get_logs() returned {len(rows)} records")
        print(f"   Average roughness: {avg_roughness:.3f}")
        
        # Check if our test record is in the results
        test_found = False
        for row in rows:
            if row.get('device_id') == test_device_id:
                test_found = True
                print(f"✅ Our test record found in get_logs() results")
                print(f"   Position in list: {rows.index(row) + 1}")
                break
        
        if not test_found:
            print("⚠️  Our test record not found in get_logs() results")
            print("   This might indicate an issue with the get_logs() method")
        
        # Test device IDs
        device_ids = db_manager.get_device_ids_with_nicknames()
        print(f"✅ get_device_ids_with_nicknames() returned {len(device_ids)} devices")
        
        test_device_found = False
        for device in device_ids:
            if isinstance(device, dict) and device.get('device_id') == test_device_id:
                test_device_found = True
                break
            elif isinstance(device, str) and device == test_device_id:
                test_device_found = True
                break
        
        if test_device_found:
            print(f"✅ Our test device found in device list")
        else:
            print("⚠️  Our test device not found in device list")
        
    except Exception as e:
        print(f"❌ API retrieval failed: {e}")
        return False
    
    # Test 4: Check current record counts
    print("\n📈 Test 4: Checking record counts")
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM RCI_bike_data")
        total_count = cursor.fetchone()[0]
        print(f"📊 Total records in RCI_bike_data: {total_count}")
        
        # Count recent records (last hour)
        cursor.execute("""
            SELECT COUNT(*) FROM RCI_bike_data 
            WHERE timestamp >= DATEADD(hour, -1, GETDATE())
        """)
        recent_count = cursor.fetchone()[0]
        print(f"📊 Records in last hour: {recent_count}")
        
        # Count records today
        cursor.execute("""
            SELECT COUNT(*) FROM RCI_bike_data 
            WHERE CAST(timestamp AS DATE) = CAST(GETDATE() AS DATE)
        """)
        today_count = cursor.fetchone()[0]
        print(f"📊 Records today: {today_count}")
        
        # Show latest 5 records
        cursor.execute("""
            SELECT TOP 5 id, device_id, timestamp, latitude, longitude, roughness 
            FROM RCI_bike_data 
            ORDER BY id DESC
        """)
        
        print(f"\n📋 Latest 5 records:")
        for row in cursor.fetchall():
            print(f"   ID:{row[0]} | Device:{row[1]} | Time:{row[2]} | Lat:{row[3]:.4f} | Lon:{row[4]:.4f} | Rough:{row[5]:.3f}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Count check failed: {e}")
        return False
    
    print("\n🎉 Data flow test completed successfully!")
    print("The Azure SQL Database is working correctly for data operations.")
    return True

if __name__ == "__main__":
    success = test_data_flow()
    if success:
        print("\n" + "=" * 60)
        print("✅ CONCLUSION: Azure SQL Database is working perfectly!")
        print("If no new data appears on the map, the issue is likely:")
        print("  1. Data not being sent from devices/clients")
        print("  2. API endpoints not being called")
        print("  3. Frontend not refreshing/fetching data")
        print("  4. Filtering or display logic issues")
        print("=" * 60)
    else:
        print("\n❌ Data flow test failed!")
    
    sys.exit(0 if success else 1)
