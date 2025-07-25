#!/usr/bin/env python3
"""
Simple Azure SQL Database connection test - step by step
"""

import os
import sys
import time
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

# Load .env for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print("🚀 Simple Azure SQL Database Test")
print("=" * 50)

# Step 1: Load environment variables
print("\n📋 Step 1: Loading Environment")
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded")
except Exception as e:
    print(f"❌ Failed to load environment: {e}")
    sys.exit(1)

# Step 2: Check environment variables
print("\n📋 Step 2: Checking Environment Variables")
required_vars = ["AZURE_SQL_SERVER", "AZURE_SQL_DATABASE", "AZURE_SQL_USER", "AZURE_SQL_PASSWORD", "AZURE_SQL_PORT"]
env_status = {}

for var in required_vars:
    value = os.getenv(var)
    env_status[var] = value is not None
    display_value = "***" if var == "AZURE_SQL_PASSWORD" and value else value
    status = "✅" if value else "❌"
    print(f"  {status} {var}: {display_value}")

if not all(env_status.values()):
    print("❌ Missing required environment variables!")
    sys.exit(1)

print("✅ All environment variables present")

# Step 3: Check pyodbc
print("\n📋 Step 3: Checking pyodbc")
try:
    import pyodbc
    print("✅ pyodbc imported successfully")
    
    drivers = pyodbc.drivers()
    print(f"✅ Found {len(drivers)} ODBC drivers:")
    for driver in drivers:
        print(f"  - {driver}")
    
    if not drivers:
        print("❌ No ODBC drivers found!")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ pyodbc not available: {e}")
    sys.exit(1)

# Step 4: Check database configuration logic
print("\n📋 Step 4: Checking Database Configuration Logic")
try:
    # Import the database module constants
    from database import USE_SQLSERVER
    print(f"✅ Database module imported")
    print(f"🔍 USE_SQLSERVER flag: {USE_SQLSERVER}")
    
    if not USE_SQLSERVER:
        print("❌ USE_SQLSERVER is False - checking why...")
        
        # Check each condition manually
        server = os.getenv("AZURE_SQL_SERVER")
        port = os.getenv("AZURE_SQL_PORT") 
        user = os.getenv("AZURE_SQL_USER")
        password = os.getenv("AZURE_SQL_PASSWORD")
        database = os.getenv("AZURE_SQL_DATABASE")
        
        print(f"  Server present: {bool(server)}")
        print(f"  Port present: {bool(port)}")
        print(f"  User present: {bool(user)}")
        print(f"  Password present: {bool(password)}")
        print(f"  Database present: {bool(database)}")
        print(f"  pyodbc available: {pyodbc is not None}")
        print(f"  pyodbc.drivers() available: {bool(pyodbc.drivers())}")
        
        sys.exit(1)
    else:
        print("✅ Database configured for SQL Server")
        
except Exception as e:
    print(f"❌ Error checking database configuration: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 5: Test raw connection without DatabaseManager
print("\n📋 Step 5: Testing Raw pyodbc Connection")
try:
    server = os.getenv("AZURE_SQL_SERVER")
    port = os.getenv("AZURE_SQL_PORT")
    user = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    database = os.getenv("AZURE_SQL_DATABASE")
    
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password}"
    )
    
    print(f"🔗 Connecting to: {server}:{port}")
    print(f"🔗 Database: {database}")
    print(f"🔗 User: {user}")
    
    start_time = time.time()
    print("🔄 Establishing connection...")
    
    conn = pyodbc.connect(conn_str, timeout=30)
    
    connection_time = time.time() - start_time
    print(f"✅ Raw connection successful in {connection_time:.2f} seconds")
    
    cursor = conn.cursor()
    
    # Test basic queries
    print("🔍 Testing basic queries...")
    
    cursor.execute("SELECT @@VERSION")
    version = cursor.fetchone()[0]
    print(f"✅ Server version: {version[:100]}...")
    
    cursor.execute("SELECT DB_NAME()")
    db_name = cursor.fetchone()[0]
    print(f"✅ Connected to database: {db_name}")
    
    cursor.execute("SELECT GETDATE()")
    server_time = cursor.fetchone()[0]
    print(f"✅ Server time: {server_time}")
    
    # Check if any RCI tables exist
    cursor.execute("SELECT COUNT(*) FROM sys.tables WHERE name LIKE 'RCI_%'")
    table_count = cursor.fetchone()[0]
    print(f"✅ Found {table_count} RCI tables")
    
    conn.close()
    print("✅ Raw connection test successful")
    
except Exception as e:
    print(f"❌ Raw connection failed: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 6: Test DatabaseManager with timeout
print("\n📋 Step 6: Testing DatabaseManager (with timeout protection)")
try:
    print("🔄 Creating DatabaseManager instance...")
    
    # Import with timeout protection
    start_time = time.time()
    
    from database import DatabaseManager, LogLevel
    
    # Create the manager
    db_manager = DatabaseManager(log_level=LogLevel.INFO)  # Use INFO instead of DEBUG to reduce output
    
    creation_time = time.time() - start_time
    print(f"✅ DatabaseManager created in {creation_time:.2f} seconds")
    
    print(f"🔍 Configuration check:")
    print(f"  - use_sqlserver: {db_manager.use_sqlserver}")
    print(f"  - log_level: {db_manager.log_level}")
    
    if not db_manager.use_sqlserver:
        print("❌ DatabaseManager not configured for SQL Server!")
        sys.exit(1)
    
    # Test connection through manager
    print("🔄 Testing connection through DatabaseManager...")
    start_time = time.time()
    
    conn = db_manager.get_connection()
    
    manager_conn_time = time.time() - start_time
    print(f"✅ DatabaseManager connection successful in {manager_conn_time:.2f} seconds")
    
    cursor = conn.cursor()
    cursor.execute("SELECT DB_NAME()")
    db_name = cursor.fetchone()[0]
    print(f"✅ Connected via manager to: {db_name}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ DatabaseManager test failed: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 All tests passed! Azure SQL Database is accessible.")
print("The issue was likely in the DatabaseManager initialization timeout.")
print("=" * 50)
