#!/usr/bin/env python3
"""
Test script to verify that the website is successfully recording data to the SQL server.

This script performs comprehensive testing of:
1. Database connectivity and table existence
2. API endpoint functionality (/bike-data)
3. Data insertion and retrieval verification
4. Data integrity checks
5. Performance verification

Run this script locally to test your deployed website.
"""

import sys
import os
import json
import time
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import random
import math

# Add the project directory to Python path for imports
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

try:
    from database import db_manager, TABLE_BIKE_DATA, TABLE_DEBUG_LOG
    from log_utils import log_info, log_error, log_debug, LogLevel, LogCategory
    DIRECT_DB_TEST = True
except ImportError as e:
    print(f"Warning: Could not import database modules: {e}")
    print("Will only test API endpoints without direct database verification.")
    DIRECT_DB_TEST = False

class WebsiteDataRecordingTester:
    """Test class for verifying website data recording functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000", use_https: bool = False):
        """Initialize the tester with website URL."""
        self.base_url = base_url.rstrip('/')
        if use_https and not self.base_url.startswith('https://'):
            self.base_url = self.base_url.replace('http://', 'https://')
        
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Test configuration
        self.test_device_id = f"test_device_{int(time.time())}"
        self.test_results = []
        
        print(f"🔍 Initializing Website Data Recording Tester")
        print(f"📍 Target URL: {self.base_url}")
        print(f"🤖 Test Device ID: {self.test_device_id}")
        print("=" * 80)
    
    def log_test_result(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log a test result."""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
        print()
    
    def test_health_endpoint(self) -> bool:
        """Test the health check endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test_result(
                        "Health Check",
                        True,
                        "Health endpoint reports healthy status",
                        {
                            "status_code": response.status_code,
                            "database_status": data.get("database", "unknown"),
                            "timestamp": data.get("timestamp", "unknown")
                        }
                    )
                    return True
                else:
                    self.log_test_result(
                        "Health Check",
                        False,
                        f"Health endpoint reports unhealthy status: {data.get('status')}",
                        {"response_data": data}
                    )
                    return False
            else:
                self.log_test_result(
                    "Health Check",
                    False,
                    f"Health endpoint returned status {response.status_code}",
                    {"status_code": response.status_code, "response_text": response.text[:500]}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Health Check",
                False,
                f"Failed to connect to health endpoint: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def generate_test_bike_data(self) -> Dict[str, Any]:
        """Generate realistic test bike data."""
        # Realistic coordinates (somewhere in the Netherlands)
        base_lat = 52.1073946
        base_lon = 5.1340406
        
        # Add small random variations
        latitude = base_lat + random.uniform(-0.01, 0.01)
        longitude = base_lon + random.uniform(-0.01, 0.01)
        
        # Generate realistic z_values (60 accelerometer samples)
        z_values = []
        for i in range(60):
            # Simulate bike vibration with some road roughness
            base_vibration = 0.1 * math.sin(i * 0.5)  # Base cycling motion
            road_roughness = random.uniform(-0.2, 0.2)  # Road surface variation
            noise = random.uniform(-0.05, 0.05)  # Sensor noise
            z_values.append(base_vibration + road_roughness + noise)
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "speed": random.uniform(15.0, 35.0),  # Realistic cycling speed
            "direction": random.uniform(0.0, 360.0),
            "device_id": self.test_device_id,
            "z_values": z_values,
            "user_agent": "test-website-data-recording-script",
            "device_fp": f"test-fp-{int(time.time())}",
            "record_source_data": True  # Request source data recording
        }
    
    def test_bike_data_submission(self) -> bool:
        """Test submitting bike data to the /bike-data endpoint."""
        test_data = self.generate_test_bike_data()
        
        try:
            response = self.session.post(
                f"{self.base_url}/bike-data",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "ok" and "roughness" in response_data:
                    roughness = response_data["roughness"]
                    self.log_test_result(
                        "Bike Data Submission",
                        True,
                        f"Successfully submitted bike data",
                        {
                            "status_code": response.status_code,
                            "roughness": roughness,
                            "response_status": response_data.get("status"),
                            "latitude": test_data["latitude"],
                            "longitude": test_data["longitude"],
                            "speed": test_data["speed"],
                            "z_values_count": len(test_data["z_values"])
                        }
                    )
                    return True
                else:
                    self.log_test_result(
                        "Bike Data Submission",
                        False,
                        f"Unexpected response format: {response_data}",
                        {"response_data": response_data}
                    )
                    return False
            elif response.status_code == 422:
                # Validation error
                error_detail = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test_result(
                    "Bike Data Submission",
                    False,
                    f"Data validation failed (422): {error_detail}",
                    {"status_code": response.status_code, "error_detail": error_detail}
                )
                return False
            else:
                self.log_test_result(
                    "Bike Data Submission",
                    False,
                    f"HTTP error {response.status_code}",
                    {"status_code": response.status_code, "response_text": response.text[:500]}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Bike Data Submission",
                False,
                f"Failed to submit bike data: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_multiple_submissions(self, count: int = 3) -> bool:
        """Test multiple data submissions to verify consistent recording."""
        success_count = 0
        
        for i in range(count):
            print(f"🔄 Submitting test data {i+1}/{count}...")
            test_data = self.generate_test_bike_data()
            
            try:
                response = self.session.post(
                    f"{self.base_url}/bike-data",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("status") == "ok":
                        success_count += 1
                        print(f"    ✅ Submission {i+1} successful (roughness: {response_data.get('roughness', 'N/A')})")
                    else:
                        print(f"    ❌ Submission {i+1} failed: {response_data}")
                else:
                    print(f"    ❌ Submission {i+1} failed with status {response.status_code}")
            except Exception as e:
                print(f"    ❌ Submission {i+1} exception: {e}")
            
            # Brief delay between submissions
            time.sleep(1)
        
        success_rate = success_count / count
        success = success_rate >= 0.8  # 80% success rate threshold
        
        self.log_test_result(
            "Multiple Data Submissions",
            success,
            f"Successfully submitted {success_count}/{count} data entries ({success_rate:.1%} success rate)",
            {
                "total_submissions": count,
                "successful_submissions": success_count,
                "success_rate": f"{success_rate:.1%}",
                "threshold": "80%"
            }
        )
        
        return success
    
    def test_direct_database_connectivity(self) -> bool:
        """Test direct database connectivity (if available)."""
        if not DIRECT_DB_TEST:
            self.log_test_result(
                "Direct Database Test",
                False,
                "Database modules not available for direct testing",
                {"reason": "Import error - testing in API-only mode"}
            )
            return False
        
        try:
            # Test database connection
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                # Test table existence
                if db_manager.use_sqlserver:
                    cursor.execute("SELECT name FROM sys.tables WHERE name LIKE 'RCI_%'")
                else:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'RCI_%'")
                
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                required_tables = [TABLE_BIKE_DATA, TABLE_DEBUG_LOG]
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    self.log_test_result(
                        "Direct Database Test",
                        False,
                        f"Missing required tables: {missing_tables}",
                        {"existing_tables": tables, "missing_tables": missing_tables}
                    )
                    return False
                else:
                    self.log_test_result(
                        "Direct Database Test",
                        True,
                        f"Database connectivity verified, {len(tables)} tables found",
                        {
                            "database_type": "SQL Server" if db_manager.use_sqlserver else "SQLite",
                            "tables_found": tables
                        }
                    )
                    return True
            else:
                conn.close()
                self.log_test_result(
                    "Direct Database Test",
                    False,
                    "Database query test failed",
                    {"query_result": result}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Direct Database Test",
                False,
                f"Database connectivity failed: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_data_persistence(self) -> bool:
        """Test that submitted data is actually persisted in the database."""
        if not DIRECT_DB_TEST:
            self.log_test_result(
                "Data Persistence Test",
                False,
                "Cannot verify data persistence without direct database access",
                {"reason": "Database modules not available"}
            )
            return False
        
        try:
            # Get initial count
            initial_count_query = f"SELECT COUNT(*) FROM {TABLE_BIKE_DATA} WHERE device_id = ?"
            initial_result = db_manager.execute_query(initial_count_query, (self.test_device_id,))
            initial_count = initial_result[0]['COUNT(*)'] if initial_result else 0
            
            # Submit test data
            test_data = self.generate_test_bike_data()
            response = self.session.post(
                f"{self.base_url}/bike-data",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                self.log_test_result(
                    "Data Persistence Test",
                    False,
                    f"Data submission failed with status {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
            
            # Wait a moment for data to be processed
            time.sleep(2)
            
            # Check if data was persisted
            final_result = db_manager.execute_query(initial_count_query, (self.test_device_id,))
            final_count = final_result[0]['COUNT(*)'] if final_result else 0
            
            records_added = final_count - initial_count
            
            if records_added >= 1:
                # Verify the actual data
                latest_data_query = f"""
                    SELECT latitude, longitude, speed, roughness, device_id 
                    FROM {TABLE_BIKE_DATA} 
                    WHERE device_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """
                latest_result = db_manager.execute_query(latest_data_query, (self.test_device_id,))
                
                if latest_result:
                    stored_data = latest_result[0]
                    self.log_test_result(
                        "Data Persistence Test",
                        True,
                        f"Data successfully persisted ({records_added} new records)",
                        {
                            "initial_count": initial_count,
                            "final_count": final_count,
                            "records_added": records_added,
                            "stored_latitude": stored_data.get('latitude'),
                            "stored_longitude": stored_data.get('longitude'),
                            "stored_speed": stored_data.get('speed'),
                            "stored_roughness": stored_data.get('roughness')
                        }
                    )
                    return True
                else:
                    self.log_test_result(
                        "Data Persistence Test",
                        False,
                        "Count increased but could not retrieve stored data",
                        {"records_added": records_added}
                    )
                    return False
            else:
                self.log_test_result(
                    "Data Persistence Test",
                    False,
                    "No new records found in database after submission",
                    {
                        "initial_count": initial_count,
                        "final_count": final_count,
                        "records_added": records_added
                    }
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Data Persistence Test",
                False,
                f"Data persistence test failed: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_performance(self) -> bool:
        """Test response time performance."""
        response_times = []
        
        for i in range(3):
            test_data = self.generate_test_bike_data()
            
            start_time = time.time()
            try:
                response = self.session.post(
                    f"{self.base_url}/bike-data",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
                else:
                    print(f"    ⚠️ Performance test {i+1} failed with status {response.status_code}")
            except Exception as e:
                print(f"    ⚠️ Performance test {i+1} exception: {e}")
            
            time.sleep(0.5)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            # Performance criteria: average < 5 seconds, max < 10 seconds
            performance_ok = avg_time < 5.0 and max_time < 10.0
            
            self.log_test_result(
                "Performance Test",
                performance_ok,
                f"Average response time: {avg_time:.2f}s",
                {
                    "average_time": f"{avg_time:.2f}s",
                    "min_time": f"{min_time:.2f}s",
                    "max_time": f"{max_time:.2f}s",
                    "sample_count": len(response_times),
                    "threshold": "avg < 5s, max < 10s"
                }
            )
            return performance_ok
        else:
            self.log_test_result(
                "Performance Test",
                False,
                "No successful responses for performance measurement",
                {"successful_requests": 0}
            )
            return False
    
    def cleanup_test_data(self):
        """Clean up test data from the database."""
        if not DIRECT_DB_TEST:
            print("ℹ️ Cannot clean up test data without direct database access")
            return
        
        try:
            cleanup_query = f"DELETE FROM {TABLE_BIKE_DATA} WHERE device_id = ?"
            result = db_manager.execute_query(cleanup_query, (self.test_device_id,))
            print(f"🧹 Cleaned up test data for device {self.test_device_id}")
        except Exception as e:
            print(f"⚠️ Failed to clean up test data: {e}")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary results."""
        print("🚀 Starting comprehensive website data recording tests...\n")
        
        # Run all tests
        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Direct Database", self.test_direct_database_connectivity),
            ("Single Data Submission", self.test_bike_data_submission),
            ("Multiple Data Submissions", lambda: self.test_multiple_submissions(3)),
            ("Data Persistence", self.test_data_persistence),
            ("Performance", self.test_performance)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
        
        # Generate summary
        success_rate = passed / total
        overall_success = success_rate >= 0.7  # 70% success rate for overall pass
        
        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Tests Passed: {passed}/{total} ({success_rate:.1%})")
        print(f"Overall Result: {'✅ PASS' if overall_success else '❌ FAIL'}")
        print()
        
        # Detailed results
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test_name']}: {result['message']}")
        
        print("\n" + "=" * 80)
        
        # Cleanup
        self.cleanup_test_data()
        
        return {
            "overall_success": overall_success,
            "tests_passed": passed,
            "tests_total": total,
            "success_rate": success_rate,
            "detailed_results": self.test_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def main():
    """Main function to run the tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test website data recording functionality")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL of the website (default: http://localhost:8000)")
    parser.add_argument("--https", action="store_true", 
                       help="Use HTTPS instead of HTTP")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = WebsiteDataRecordingTester(args.url, args.https)
    
    try:
        # Run tests
        results = tester.run_all_tests()
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"📄 Results saved to {args.output}")
        
        # Exit with appropriate code
        exit_code = 0 if results["overall_success"] else 1
        print(f"\n🏁 Test completed with exit code {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
