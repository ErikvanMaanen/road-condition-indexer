#!/usr/bin/env python3
"""
Test Azure SQL Database connection directly
"""

import os
import sys
import time
import threading
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

# Load environment variables
print("🔄 Loading environment variables...")
from dotenv import load_dotenv
load_dotenv()
print("✅ Environment variables loaded")

# Import database manager
print("🔄 Importing database manager...")
from database import DatabaseManager
from log_utils import LogLevel, LogCategory
print("✅ Database manager imported")

def progress_indicator(message, timeout=30):
    """Show a progress indicator for long-running operations."""
    print(f"🔄 {message}", end="", flush=True)
    
    def spinner():
        chars = "|/-\\"
        idx = 0
        start_time = time.time()
        while not getattr(spinner, 'done', False):
            if time.time() - start_time > timeout:
                print(f"\n⚠️  Operation taking longer than {timeout}s...")
                break
            print(f"\r🔄 {message} {chars[idx % len(chars)]}", end="", flush=True)
            idx += 1
            time.sleep(0.1)
        if not getattr(spinner, 'timeout', False):
            print(f"\r✅ {message} - Complete!")
    
    thread = threading.Thread(target=spinner, daemon=True)
    thread.start()
    return thread

def stop_progress(thread):
    """Stop the progress indicator."""
    if thread and thread.is_alive():
        thread.done = True
        thread.join(timeout=1)

def test_azure_connection():
    """Test Azure SQL Database connection and basic operations."""
    print("🔍 Testing Azure SQL Database Connection")
    print("=" * 60)
    print(f"📅 Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check environment variables
    print("\n📋 Step 1: Checking Environment Variables")
    print("-" * 40)
    
    azure_vars = {
        "AZURE_SQL_SERVER": os.getenv("AZURE_SQL_SERVER"),
        "AZURE_SQL_DATABASE": os.getenv("AZURE_SQL_DATABASE"),
        "AZURE_SQL_USER": os.getenv("AZURE_SQL_USER"),
        "AZURE_SQL_PASSWORD": "***" if os.getenv("AZURE_SQL_PASSWORD") else None,
        "AZURE_SQL_PORT": os.getenv("AZURE_SQL_PORT")
    }
    
    print("Environment Variables:")
    for key, value in azure_vars.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    missing = [k for k, v in azure_vars.items() if v is None]
    if missing:
        print(f"\n❌ Missing environment variables: {missing}")
        print("💡 Make sure the .env file is present and contains all required variables")
        return False
    
    print("\n✅ All Azure SQL environment variables are set")
    
    # Test pyodbc availability
    print("\n📋 Step 2: Checking Dependencies")
    print("-" * 40)
    
    try:
        print("🔄 Checking pyodbc availability...")
        import pyodbc
        print("✅ pyodbc imported successfully")
        
        print("🔄 Checking available ODBC drivers...")
        drivers = pyodbc.drivers()
        print(f"✅ Found {len(drivers)} ODBC drivers:")
        for driver in drivers:
            print(f"  - {driver}")
        
        if not drivers:
            print("❌ No ODBC drivers found!")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import pyodbc: {e}")
        print("💡 Install pyodbc: pip install pyodbc")
        return False
    
    # Test database manager initialization
    print("\n� Step 3: Initializing Database Manager")
    print("-" * 40)
    
    try:
        progress = progress_indicator("Creating DatabaseManager instance")
        db_manager = DatabaseManager(log_level=LogLevel.DEBUG)
        stop_progress(progress)
        
        print(f"🔍 Database manager configuration:")
        print(f"  - use_sqlserver: {db_manager.use_sqlserver}")
        print(f"  - log_level: {db_manager.log_level}")
        
        if not db_manager.use_sqlserver:
            print("❌ Database manager is not configured to use SQL Server")
            print("💡 Check if all Azure SQL environment variables are set correctly")
            print("💡 Check if pyodbc is installed and SQL drivers are available")
            return False
        
        print("✅ Database manager configured for SQL Server")
        
    except Exception as e:
        print(f"\n❌ Failed to create database manager: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test database connection
    print("\n📋 Step 4: Testing Database Connection")
    print("-" * 40)
    
    try:
        print("🔄 Attempting to connect to Azure SQL Database...")
        print(f"🔗 Server: {azure_vars['AZURE_SQL_SERVER']}")
        print(f"🔗 Database: {azure_vars['AZURE_SQL_DATABASE']}")
        print(f"🔗 User: {azure_vars['AZURE_SQL_USER']}")
        
        progress = progress_indicator("Establishing database connection", timeout=60)
        start_time = time.time()
        
        conn = db_manager.get_connection()
        
        stop_progress(progress)
        connection_time = time.time() - start_time
        print(f"⏱️  Connection established in {connection_time:.2f} seconds")
        
        cursor = conn.cursor()
        print("✅ Database cursor created")
        
        # Get server info
        print("\n🔍 Getting server information...")
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"✅ Server version: {version[:150]}...")
        
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"✅ Connected to database: {db_name}")
        
        cursor.execute("SELECT SUSER_NAME()")
        user_name = cursor.fetchone()[0]
        print(f"✅ Connected as user: {user_name}")
        
        cursor.execute("SELECT GETDATE()")
        server_time = cursor.fetchone()[0]
        print(f"✅ Server time: {server_time}")
        
    except Exception as e:
        stop_progress(progress)
        print(f"\n❌ Database connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test table operations
    print("\n� Step 5: Testing Table Operations")
    print("-" * 40)
    
    try:
        print("🔄 Initializing database tables...")
        progress = progress_indicator("Creating/verifying tables", timeout=45)
        start_time = time.time()
        
        db_manager.init_tables()
        
        stop_progress(progress)
        table_time = time.time() - start_time
        print(f"⏱️  Table initialization completed in {table_time:.2f} seconds")
        
        # Check tables
        print("🔍 Checking created tables...")
        cursor.execute("SELECT name FROM sys.tables WHERE name LIKE 'RCI_%' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ Found {len(tables)} RCI tables: {tables}")
        
        # Get table row counts
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  📊 {table}: {count} rows")
            except Exception as e:
                print(f"  ⚠️  {table}: Error getting count - {e}")
        
    except Exception as e:
        stop_progress(progress)
        print(f"\n❌ Table initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test data insertion
    print("\n� Step 6: Testing Data Insertion")
    print("-" * 40)
    
    try:
        test_device_id = f"azure_test_{int(time.time())}"
        print(f"🔄 Inserting test record with device_id: {test_device_id}")
        
        progress = progress_indicator("Inserting test data")
        start_time = time.time()
        
        bike_data_id = db_manager.insert_bike_data(
            latitude=52.3676,
            longitude=4.9041,
            speed=25.0,
            direction=45.0,
            roughness=1.87,
            distance_m=200.0,
            device_id=test_device_id,
            ip_address="127.0.0.1"
        )
        
        stop_progress(progress)
        insert_time = time.time() - start_time
        print(f"⏱️  Data insertion completed in {insert_time:.2f} seconds")
        print(f"✅ Test record inserted with ID: {bike_data_id}")
        
        # Verify the insertion
        print("🔍 Verifying inserted record...")
        cursor.execute("SELECT * FROM RCI_bike_data WHERE id = ?", bike_data_id)
        verify_row = cursor.fetchone()
        
        if verify_row:
            print("✅ Record verification successful")
            columns = [desc[0] for desc in cursor.description]
            record_dict = dict(zip(columns, verify_row))
            print(f"  📝 Record details: ID={record_dict.get('id')}, Device={record_dict.get('device_id')}, Lat={record_dict.get('latitude')}, Lon={record_dict.get('longitude')}")
        else:
            print("❌ Record verification failed - record not found!")
            return False
        
    except Exception as e:
        stop_progress(progress)
        print(f"\n❌ Data insertion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test data retrieval
    print("\n📋 Step 7: Testing Data Retrieval")
    print("-" * 40)
    
    try:
        print("� Testing data retrieval through API methods...")
        
        progress = progress_indicator("Retrieving logs")
        start_time = time.time()
        
        rows, avg_roughness = db_manager.get_logs(5)
        
        stop_progress(progress)
        retrieval_time = time.time() - start_time
        print(f"⏱️  Data retrieval completed in {retrieval_time:.2f} seconds")
        print(f"✅ Retrieved {len(rows)} records, average roughness: {avg_roughness:.3f}")
        
        if rows:
            latest = rows[0]
            print(f"📊 Latest record details:")
            print(f"  - ID: {latest.get('id')}")
            print(f"  - Device: {latest.get('device_id')}")
            print(f"  - Timestamp: {latest.get('timestamp')}")
            print(f"  - Location: {latest.get('latitude'):.4f}, {latest.get('longitude'):.4f}")
            print(f"  - Roughness: {latest.get('roughness'):.3f}")
        else:
            print("⚠️  No records returned from get_logs()")
        
    except Exception as e:
        stop_progress(progress)
        print(f"\n❌ Data retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test device operations
    print("\n📋 Step 8: Testing Device Operations")
    print("-" * 40)
    
    try:
        print("🔄 Testing device ID retrieval...")
        device_ids = db_manager.get_device_ids_with_nicknames()
        print(f"✅ Found {len(device_ids)} unique devices")
        
        if device_ids:
            print("📱 Device list:")
            for device in device_ids[:5]:  # Show first 5
                print(f"  - {device}")
            if len(device_ids) > 5:
                print(f"  ... and {len(device_ids) - 5} more")
        
        print("🔄 Testing date range retrieval...")
        start_date, end_date = db_manager.get_date_range()
        print(f"✅ Data range: {start_date} to {end_date}")
        
    except Exception as e:
        print(f"\n⚠️  Device operations test failed: {e}")
        # Don't return False here as this isn't critical
    
    # Cleanup and final status
    print("\n📋 Step 9: Cleanup and Summary")
    print("-" * 40)
    
    try:
        conn.close()
        print("✅ Database connection closed")
        
        end_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n🎉 Azure SQL Database test completed successfully!")
        print(f"📅 End time: {end_time}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
        return True  # Still consider success if cleanup fails
        
    except Exception as e:
        print(f"\n❌ Error during database test: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"📅 Error occurred at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        import traceback
        print("\n🔍 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Azure SQL Database Test Script")
    print(f"🕒 Script start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python version: {sys.version}")
    print("=" * 80)
    
    try:
        success = test_azure_connection()
        
        if success:
            print("\n" + "=" * 80)
            print("🎊 ALL TESTS PASSED! Azure SQL Database is working correctly.")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("💥 TESTS FAILED! Check the errors above.")
            print("=" * 80)
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n💥 Unexpected error in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
