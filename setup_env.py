#!/usr/bin/env python3
"""Environment setup and database connectivity verification for Road Condition Indexer.

This script verifies that all required environment variables are set and tests 
database connectivity using the new SQLAlchemy-based database manager.

The application supports two database backends:
1. Azure SQL Server (primary) - using SQLAlchemy with pymssql driver
2. SQLite (fallback) - using SQLAlchemy with local database file

If Azure SQL environment variables are not provided, the application will
automatically fall back to SQLite for local development.
"""

import os
import sys
import warnings
from pathlib import Path

# Suppress warnings for clean output
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

def check_python_version():
    """Verify Python version compatibility."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_required_packages():
    """Check if required packages are installed."""
    required_packages = [
        'sqlalchemy',
        'fastapi', 
        'pymssql',
        'numpy',
        'scipy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ Package '{package}' is available")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ Package '{package}' is missing")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install missing packages with: pip install -r requirements.txt")
        sys.exit(1)

def check_azure_sql_env_vars():
    """Check Azure SQL environment variables."""
    required_vars = [
        'AZURE_SQL_SERVER',
        'AZURE_SQL_DATABASE', 
        'AZURE_SQL_USER',
        'AZURE_SQL_PASSWORD',
        'AZURE_SQL_PORT',
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"⚠️  Azure SQL environment variables missing: {', '.join(missing)}")
        print("   Application will fall back to SQLite database")
        return False
    else:
        print("✅ Azure SQL environment variables are configured")
        return True

def test_database_connection():
    """Test database connectivity using the application's database manager."""
    try:
        # Import the application's database manager
        from database import DatabaseManager
        
        print("\n🔄 Testing database connectivity...")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        if db_manager.use_sqlserver:
            print("📊 Using Azure SQL Server backend")
            server = os.getenv("AZURE_SQL_SERVER")
            database = os.getenv("AZURE_SQL_DATABASE")
            print(f"   Server: {server}")
            print(f"   Database: {database}")
        else:
            print("📁 Using SQLite backend")
            db_path = Path(__file__).parent / "RCI_local.db"
            print(f"   Database file: {db_path}")
        
        # Test basic connectivity
        result = db_manager.execute_scalar("SELECT 1")
        if result == 1:
            print("✅ Database connection successful")
            
            # Test table initialization
            print("🔄 Testing table initialization...")
            db_manager.init_tables()
            print("✅ Database tables initialized successfully")
            
            # Test a simple query
            print("🔄 Testing basic database operations...")
            tables_result = db_manager.execute_query(
                "SELECT name FROM sys.tables WHERE name LIKE 'RCI_%'" if db_manager.use_sqlserver 
                else "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'RCI_%'"
            )
            
            table_count = len(tables_result) if tables_result else 0
            print(f"✅ Found {table_count} RCI tables in database")
            
            return True
        else:
            print("❌ Database connection test failed")
            return False
            
    except Exception as exc:
        print(f"❌ Database connection failed: {exc}")
        return False

def main():
    """Main setup verification function."""
    print("🚀 Road Condition Indexer - Environment Setup Verification")
    print("=" * 60)
    
    # Check Python version
    check_python_version()
    
    # Check required packages
    print("\n📦 Checking required packages...")
    check_required_packages()
    
    # Check environment variables
    print("\n🔧 Checking environment configuration...")
    azure_sql_available = check_azure_sql_env_vars()
    
    # Test database connection
    db_success = test_database_connection()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Setup Verification Summary:")
    print(f"   Python Version: ✅")
    print(f"   Required Packages: ✅")
    print(f"   Azure SQL Config: {'✅' if azure_sql_available else '⚠️  (using SQLite fallback)'}")
    print(f"   Database Connection: {'✅' if db_success else '❌'}")
    
    if db_success:
        print("\n🎉 Environment setup verification completed successfully!")
        print("\nYou can now start the application with:")
        print("   uvicorn main:app --reload --host 0.0.0.0")
    else:
        print("\n❌ Environment setup verification failed!")
        print("Please check the error messages above and fix any issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()
