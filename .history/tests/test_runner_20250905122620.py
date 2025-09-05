#!/usr/bin/env python3
"""
Consolidated Test Runner for Road Condition Indexer

This script provides a unified interface for running all tests in the project,
including SQL connectivity tests and comprehensive data flow tests.

Usage:
    python test_runner.py [--test-type TYPE] [--verbose]
    
Test Types:
    all           - Run all available tests (default)
    sql           - Run only SQL connectivity tests
    data-flow     - Run only comprehensive data flow tests
    
Options:
    --verbose     - Enable verbose output
    --help        - Show this help message
"""

import sys
import os
import time
import argparse
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
project_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_dir))

class TestRunner:
    """Manages and executes test suites."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: Dict[str, Any] = {
            "tests": [],
            "start_time": time.time(),
            "total_duration": 0.0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{timestamp}] [{level}] {message}")
    
    def run_sql_connectivity_tests(self) -> bool:
        """Run SQL connectivity tests."""
        self.log("Running SQL connectivity tests...", "INFO")
        
        try:
            # Import SQL connectivity tester
            from tests.extended.sql_connectivity_tests import SQLConnectivityTester, ConnectivityTestResult
            
            # Create tester instance
            tester = SQLConnectivityTester(timeout_seconds=30, retry_attempts=3)
            
            # Run tests
            report = tester.run_comprehensive_tests()
            
            # Process results
            test_result = {
                "name": "SQL Connectivity Tests",
                "passed": report.overall_status == ConnectivityTestResult.SUCCESS,
                "duration": report.total_duration_ms / 1000.0,
                "details": {
                    "overall_status": report.overall_status.value,
                    "individual_tests": len(report.tests),
                    "recommendations": len(report.recommendations)
                }
            }
            
            self.results["tests"].append(test_result)
            
            if test_result["passed"]:
                self.results["passed"] += 1
                self.log("✅ SQL connectivity tests PASSED", "INFO")
            else:
                self.results["failed"] += 1
                self.log("❌ SQL connectivity tests FAILED", "ERROR")
                
            return test_result["passed"]
            
        except Exception as e:
            self.log(f"Error running SQL connectivity tests: {e}", "ERROR")
            self.results["errors"].append(f"SQL connectivity tests: {e}")
            self.results["failed"] += 1
            return False
    
    def run_data_flow_tests(self) -> bool:
        """Run comprehensive data flow tests."""
        self.log("Running comprehensive data flow tests...", "INFO")
        
        try:
            # Import data flow test
            from tests.core.test_comprehensive_data_flow import ComprehensiveDataFlowTest
            
            # Create test instance
            test_instance = ComprehensiveDataFlowTest()
            
            # Run tests
            success = test_instance.run_all_tests()
            
            # Get test results
            test_result = {
                "name": "Comprehensive Data Flow Tests",
                "passed": success,
                "duration": 0.0,  # Will be calculated from individual tests
                "details": {
                    "individual_tests": len(test_instance.test_results),
                    "passed_tests": sum(1 for t in test_instance.test_results if t["success"]),
                    "failed_tests": sum(1 for t in test_instance.test_results if not t["success"])
                }
            }
            
            # Calculate total duration
            total_duration = 0.0
            for test in test_instance.test_results:
                if "duration" in test.get("details", {}):
                    total_duration += test["details"]["duration"]
            test_result["duration"] = total_duration
            
            self.results["tests"].append(test_result)
            
            if test_result["passed"]:
                self.results["passed"] += 1
                self.log("✅ Data flow tests PASSED", "INFO")
            else:
                self.results["failed"] += 1
                self.log("❌ Data flow tests FAILED", "ERROR")
                
            return test_result["passed"]
            
        except Exception as e:
            self.log(f"Error running data flow tests: {e}", "ERROR")
            self.results["errors"].append(f"Data flow tests: {e}")
            self.results["failed"] += 1
            return False
    
    def run_specific_test_type(self, test_type: str) -> bool:
        """Run a specific type of test."""
        if test_type == "sql":
            return self.run_sql_connectivity_tests()
        elif test_type == "data-flow":
            return self.run_data_flow_tests()
        else:
            self.log(f"Unknown test type: {test_type}", "ERROR")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all available tests."""
        self.log("Starting comprehensive test suite...", "INFO")
        
        all_passed = True
        
        # Run SQL connectivity tests
        if not self.run_sql_connectivity_tests():
            all_passed = False
        
        # Run data flow tests
        if not self.run_data_flow_tests():
            all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print a summary of test results."""
        self.results["total_duration"] = time.time() - self.results["start_time"]
        
        print("\n" + "=" * 70)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 70)
        
        # Overall status
        if self.results["failed"] == 0 and len(self.results["errors"]) == 0:
            print("✅ Overall Status: ALL TESTS PASSED")
        else:
            print("❌ Overall Status: SOME TESTS FAILED")
        
        print(f"⏱️  Total Duration: {self.results['total_duration']:.2f}s")
        print(f"📈 Tests Passed: {self.results['passed']}")
        print(f"📉 Tests Failed: {self.results['failed']}")
        
        if self.results["errors"]:
            print(f"🚨 Errors: {len(self.results['errors'])}")
        
        print()
        
        # Individual test results
        if self.results["tests"]:
            print("📋 Individual Test Results:")
            print("-" * 40)
            
            for test in self.results["tests"]:
                status = "✅ PASS" if test["passed"] else "❌ FAIL"
                print(f"{status} {test['name']}")
                print(f"   Duration: {test['duration']:.2f}s")
                
                if "details" in test:
                    for key, value in test["details"].items():
                        print(f"   {key.replace('_', ' ').title()}: {value}")
                print()
        
        # Errors
        if self.results["errors"]:
            print("🚨 Errors:")
            print("-" * 40)
            for error in self.results["errors"]:
                print(f"   {error}")
            print()


def main():
    """Main function to run tests."""
    parser = argparse.ArgumentParser(
        description="Consolidated Test Runner for Road Condition Indexer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Types:
    all           - Run all available tests (default)
    sql           - Run only SQL connectivity tests
    data-flow     - Run only comprehensive data flow tests

Examples:
    python test_runner.py                    # Run all tests
    python test_runner.py --test-type sql    # Run only SQL tests
    python test_runner.py --verbose          # Run with verbose output
        """
    )
    
    parser.add_argument(
        "--test-type",
        choices=["all", "sql", "data-flow"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner(verbose=args.verbose)
    
    print("🧪 Road Condition Indexer - Test Runner")
    print("=" * 50)
    print(f"Test Type: {args.test_type}")
    print(f"Verbose: {args.verbose}")
    print()
    
    # Run tests
    try:
        if args.test_type == "all":
            success = runner.run_all_tests()
        else:
            success = runner.run_specific_test_type(args.test_type)
        
        # Print summary
        runner.print_summary()
        
        # Exit with appropriate code
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
