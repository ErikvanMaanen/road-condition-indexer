#!/usr/bin/env python3
"""
Standalone SQL Connectivity Test Script for Road Condition Indexer

This script can be run independently to test SQL Server connectivity
before starting the main application. It provides detailed diagnostics
and recommendations for connectivity issues.

Usage:
    python tests/test_sql_connectivity.py
    
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
# ...existing code...
