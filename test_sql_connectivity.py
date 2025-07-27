#!/usr/bin/env python3
"""
Standalone SQL Connectivity Test Script for Road Condition Indexer

This script can be run independently to test SQL Server connectivity
before starting the main application. It provides detailed diagnostics
and recommendations for connectivity issues.

Usage:
    python test_sql_connectivity.py
    
Environment Variables Required:
    - AZURE_SQL_SERVER
    - AZURE_SQL_DATABASE  
    - AZURE_SQL_USER
    - AZURE_SQL_PASSWORD
    - AZURE_SQL_PORT (optional, defaults to 1433)
"""

import sys
import os
from pathlib import Path

# Add the current directory to the Python path to import our modules
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main function to run SQL connectivity tests."""
    print("=" * 70)
    print("🔍 SQL Server Connectivity Test for Road Condition Indexer")
    print("=" * 70)
    print()
    
    try:
        # Import our SQL connectivity tester
        from sql_connectivity_tests import SQLConnectivityTester, ConnectivityTestResult
        
        # Create tester instance with reasonable timeouts
        tester = SQLConnectivityTester(timeout_seconds=30, retry_attempts=3)
        
        # Run comprehensive tests
        print("🧪 Running comprehensive SQL connectivity tests...")
        print()
        
        report = tester.run_comprehensive_tests()
        
        # Print detailed results
        print("\n" + "=" * 70)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 70)
        
        # Overall status
        status_emoji = {
            ConnectivityTestResult.SUCCESS: "✅",
            ConnectivityTestResult.WARNING: "⚠️",
            ConnectivityTestResult.FAILED: "❌"
        }.get(report.overall_status, "❓")
        
        print(f"{status_emoji} Overall Status: {report.overall_status.value}")
        print(f"⏱️  Total Duration: {report.total_duration_ms:.1f}ms")
        print()
        
        # Individual test results
        print("📋 Individual Test Results:")
        print("-" * 40)
        
        for test in report.tests:
            test_emoji = {
                ConnectivityTestResult.SUCCESS: "✅",
                ConnectivityTestResult.WARNING: "⚠️", 
                ConnectivityTestResult.FAILED: "❌",
                ConnectivityTestResult.TIMEOUT: "⏱️",
                ConnectivityTestResult.DNS_ERROR: "🌐",
                ConnectivityTestResult.AUTH_ERROR: "🔑",
                ConnectivityTestResult.CONNECTION_ERROR: "🔌"
            }.get(test.result, "❓")
            
            print(f"{test_emoji} {test.test_name}")
            print(f"   Status: {test.result.value}")
            print(f"   Duration: {test.duration_ms:.1f}ms")
            print(f"   Message: {test.message}")
            
            if test.details:
                print(f"   Details: {test.details}")
            print()
        
        # Environment information
        print("🔧 Environment Information:")
        print("-" * 40)
        for key, value in report.environment_info.items():
            # Mask sensitive information
            if "password" in key.lower() or "secret" in key.lower():
                value = "***"
            print(f"   {key}: {value}")
        print()
        
        # Recommendations
        if report.recommendations:
            print("💡 Recommendations:")
            print("-" * 40)
            for recommendation in report.recommendations:
                print(f"   {recommendation}")
            print()
        
        # Exit code based on results
        if report.overall_status == ConnectivityTestResult.SUCCESS:
            print("🎉 All tests passed! Your SQL Server connectivity is working properly.")
            return 0
        elif report.overall_status == ConnectivityTestResult.WARNING:
            print("⚠️  Tests completed with warnings. Check the recommendations above.")
            return 1
        else:
            print("❌ Tests failed. Please review the errors and recommendations above.")
            return 2
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Make sure you're running this script from the correct directory.")
        print("💡 Install required dependencies: pip install -r requirements.txt")
        return 3
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("💡 Check your environment variables and network connectivity.")
        return 4


if __name__ == "__main__":
    sys.exit(main())
