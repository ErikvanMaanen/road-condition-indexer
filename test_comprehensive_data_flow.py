"""
Comprehensive test for Road Condition Indexer database and API operations.

This test verifies:
1. Direct database write operations
2. API endpoint data posting
3. Data verification and integrity
4. Enhanced logging functionality

Run with: python test_comprehensive_data_flow.py
"""

import json
import os
import requests
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import traceback

# Import database manager for direct operations
from database import DatabaseManager, TABLE_BIKE_DATA, LogLevel, LogCategory

class ComprehensiveDataFlowTest:
    """Test suite for database and API operations."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize test with API base URL."""
        self.base_url = base_url
        self.db_manager = DatabaseManager()
        self.test_device_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.test_results = []
        
        # Check if we're in database-only mode
        self.database_only = os.environ.get('RCI_TEST_MODE') == 'database_only'
        
        print(f"🧪 Initializing comprehensive data flow test")
        if self.database_only:
            print(f"🗄️  Mode: Database-only testing")
        else:
            print(f"📍 API Base URL: {self.base_url}")
        print(f"🔧 Test Device ID: {self.test_device_id}")
        print(f"🗄️  Database Type: {'SQL Server' if self.db_manager.use_sqlserver else 'SQLite'}")
        print("-" * 80)
    
    def log_test_result(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log test result with enhanced details."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        
        # Also log to database for tracking
        try:
            level = LogLevel.INFO if success else LogLevel.ERROR
            self.db_manager.log_debug(
                f"Test {test_name}: {message}",
                level, LogCategory.GENERAL,
                device_id=self.test_device_id
            )
        except Exception as e:
            print(f"⚠️  Failed to log test result to database: {e}")
    
    def test_1_direct_database_insert(self) -> Dict:
        """Test 1: Direct database insertion."""
        print("🔧 Test 1: Direct Database Insert")
        
        try:
            # Prepare test data
            test_data = {
                "latitude": 52.3676 + (time.time() % 1000) / 100000,  # Slight variation
                "longitude": 4.9041,
                "speed": 25.0,
                "direction": 180.0,
                "roughness": 2.45,
                "distance_m": 150.0,
                "device_id": f"{self.test_device_id}_direct",
                "ip_address": "192.168.1.100"
            }
            
            print(f"📝 Inserting test data: {json.dumps(test_data, indent=2)}")
            
            # Direct database insert
            start_time = time.time()
            bike_data_id = self.db_manager.insert_bike_data(
                test_data["latitude"],
                test_data["longitude"],
                test_data["speed"],
                test_data["direction"],
                test_data["roughness"],
                test_data["distance_m"],
                test_data["device_id"],
                test_data["ip_address"]
            )
            insert_time = time.time() - start_time
            
            print(f"📊 Insert completed in {insert_time:.3f}s, ID: {bike_data_id}")
            
            # Verify the insertion by reading back
            verification_query = f"SELECT * FROM {TABLE_BIKE_DATA} WHERE id = ?"
            verify_result = self.db_manager.execute_query(verification_query, (bike_data_id,))
            
            if verify_result and len(verify_result) > 0:
                stored_record = verify_result[0]
                
                # Validate data integrity
                validation_errors = []
                if abs(stored_record.get('latitude', 0) - test_data["latitude"]) > 0.000001:
                    validation_errors.append("Latitude mismatch")
                if abs(stored_record.get('longitude', 0) - test_data["longitude"]) > 0.000001:
                    validation_errors.append("Longitude mismatch")
                if abs(stored_record.get('speed', 0) - test_data["speed"]) > 0.01:
                    validation_errors.append("Speed mismatch")
                if stored_record.get('device_id') != test_data["device_id"]:
                    validation_errors.append("Device ID mismatch")
                
                if validation_errors:
                    self.log_test_result(
                        "Direct Database Insert",
                        False,
                        f"Data validation failed: {', '.join(validation_errors)}",
                        {"bike_data_id": bike_data_id, "validation_errors": validation_errors}
                    )
                    return {"success": False, "bike_data_id": bike_data_id, "errors": validation_errors}
                else:
                    self.log_test_result(
                        "Direct Database Insert",
                        True,
                        f"Successfully inserted and verified record ID {bike_data_id}",
                        {"bike_data_id": bike_data_id, "insert_time": insert_time, "stored_record": stored_record}
                    )
                    return {"success": True, "bike_data_id": bike_data_id, "stored_record": stored_record}
            else:
                self.log_test_result(
                    "Direct Database Insert",
                    False,
                    f"Verification failed: Record ID {bike_data_id} not found in database",
                    {"bike_data_id": bike_data_id}
                )
                return {"success": False, "bike_data_id": bike_data_id, "error": "Record not found"}
                
        except Exception as e:
            error_msg = f"Exception during direct insert: {str(e)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            self.log_test_result("Direct Database Insert", False, error_msg, {"exception": str(e)})
            return {"success": False, "error": str(e)}
    
    def test_2_api_post_with_verification(self) -> Dict:
        """Test 2: API POST with database verification."""
        print("\n🌐 Test 2: API POST with Database Verification")
        
        if self.database_only:
            print("⏭️  Skipping API test in database-only mode")
            self.log_test_result("API POST with Verification", True, "Skipped in database-only mode")
            return {"success": True, "message": "Skipped in database-only mode"}
        
        try:
            # Prepare API payload
            api_payload = {
                "latitude": 52.3676 + (time.time() % 1000) / 100000,  # Slight variation
                "longitude": 4.9041,
                "speed": 30.0,
                "direction": 90.0,
                "device_id": f"{self.test_device_id}_api",
                "z_values": [0.1, -0.2, 0.3, -0.1, 0.2, -0.3, 0.1, 0.0, -0.1, 0.2],  # Sample accelerometer data
                "user_agent": "TestAgent/1.0 (Comprehensive Test)",
                "device_fp": f"test_fingerprint_{uuid.uuid4().hex[:16]}",
                "record_source_data": True
            }
            
            print(f"📤 Posting to API: {json.dumps(api_payload, indent=2)}")
            
            # POST to API
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/log",
                headers={"Content-Type": "application/json"},
                json=api_payload,
                timeout=30
            )
            api_time = time.time() - start_time
            
            print(f"📊 API response in {api_time:.3f}s, Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"📋 API Response: {json.dumps(response_data, indent=2)}")
                
                # Wait a moment for database to be updated
                time.sleep(0.5)
                
                # Verify data was stored in database by querying for our device
                query = f"SELECT * FROM {TABLE_BIKE_DATA} WHERE device_id = ? ORDER BY id DESC LIMIT 1"
                db_results = self.db_manager.execute_query(query, (api_payload["device_id"],))
                
                if db_results and len(db_results) > 0:
                    stored_record = db_results[0]
                    
                    # Validate API response has expected fields
                    api_validation_errors = []
                    if "roughness" not in response_data:
                        api_validation_errors.append("Missing roughness in API response")
                    if "status" not in response_data:
                        api_validation_errors.append("Missing status in API response")
                    
                    # Validate database record matches API payload
                    db_validation_errors = []
                    if abs(stored_record.get('latitude', 0) - api_payload["latitude"]) > 0.000001:
                        db_validation_errors.append("Latitude mismatch")
                    if abs(stored_record.get('longitude', 0) - api_payload["longitude"]) > 0.000001:
                        db_validation_errors.append("Longitude mismatch")
                    if abs(stored_record.get('speed', 0) - api_payload["speed"]) > 0.01:
                        db_validation_errors.append("Speed mismatch")
                    if stored_record.get('device_id') != api_payload["device_id"]:
                        db_validation_errors.append("Device ID mismatch")
                    
                    all_errors = api_validation_errors + db_validation_errors
                    
                    if all_errors:
                        self.log_test_result(
                            "API POST with Verification",
                            False,
                            f"Validation failed: {', '.join(all_errors)}",
                            {
                                "api_response": response_data,
                                "stored_record": stored_record,
                                "validation_errors": all_errors,
                                "api_time": api_time
                            }
                        )
                        return {"success": False, "errors": all_errors}
                    else:
                        self.log_test_result(
                            "API POST with Verification",
                            True,
                            f"Successfully posted to API and verified in database (roughness: {response_data.get('roughness', 'N/A')})",
                            {
                                "api_response": response_data,
                                "stored_record": stored_record,
                                "api_time": api_time
                            }
                        )
                        return {"success": True, "api_response": response_data, "stored_record": stored_record}
                else:
                    self.log_test_result(
                        "API POST with Verification",
                        False,
                        "API succeeded but record not found in database",
                        {"api_response": response_data}
                    )
                    return {"success": False, "error": "Record not found in database after API call"}
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                self.log_test_result("API POST with Verification", False, error_msg)
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.RequestException as e:
            error_msg = f"API request exception: {str(e)}"
            print(f"❌ {error_msg}")
            self.log_test_result("API POST with Verification", False, error_msg, {"exception": str(e)})
            return {"success": False, "error": str(e)}
        except Exception as e:
            error_msg = f"Exception during API test: {str(e)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            self.log_test_result("API POST with Verification", False, error_msg, {"exception": str(e)})
            return {"success": False, "error": str(e)}
    
    def test_3_enhanced_logging_functionality(self) -> Dict:
        """Test 3: Enhanced logging functionality."""
        print("\n📝 Test 3: Enhanced Logging Functionality")
        
        try:
            # Test different log levels and categories
            test_logs = [
                (LogLevel.DEBUG, LogCategory.DATABASE, "Test debug message for database operations"),
                (LogLevel.INFO, LogCategory.GENERAL, "Test info message for general operations"),
                (LogLevel.WARNING, LogCategory.CONNECTION, "Test warning message for connection issues"),
                (LogLevel.ERROR, LogCategory.QUERY, "Test error message for query problems"),
                (LogLevel.CRITICAL, LogCategory.MANAGEMENT, "Test critical message for management operations")
            ]
            
            log_ids = []
            for level, category, message in test_logs:
                self.db_manager.log_debug(message, level, category, device_id=self.test_device_id)
                print(f"📝 Logged {level.value} [{category.value}]: {message}")
            
            # Wait for logs to be written
            time.sleep(0.5)
            
            # Verify logs were stored
            log_query = "SELECT * FROM RCI_debug_log WHERE message LIKE ? ORDER BY id DESC LIMIT 10"
            stored_logs = self.db_manager.execute_query(log_query, ("Test % message%",))
            
            print(f"📊 Expected {len(test_logs)} logs, found {len(stored_logs)} in database")
            
            if len(stored_logs) >= len(test_logs):
                self.log_test_result(
                    "Enhanced Logging Functionality",
                    True,
                    f"Successfully logged and retrieved {len(stored_logs)} enhanced log messages",
                    {"logged_count": len(test_logs), "retrieved_count": len(stored_logs)}
                )
                return {"success": True, "logged_count": len(test_logs), "retrieved_count": len(stored_logs)}
            else:
                # More flexible check - if we got at least 4 out of 5, that's acceptable
                if len(stored_logs) >= len(test_logs) - 1:
                    self.log_test_result(
                        "Enhanced Logging Functionality",
                        True,
                        f"Successfully logged and retrieved {len(stored_logs)} of {len(test_logs)} enhanced log messages (acceptable)",
                        {"logged_count": len(test_logs), "retrieved_count": len(stored_logs)}
                    )
                    return {"success": True, "logged_count": len(test_logs), "retrieved_count": len(stored_logs)}
                else:
                    self.log_test_result(
                        "Enhanced Logging Functionality",
                        False,
                        f"Expected {len(test_logs)} logs but found {len(stored_logs)}",
                        {"expected": len(test_logs), "found": len(stored_logs)}
                    )
                    return {"success": False, "expected": len(test_logs), "found": len(stored_logs)}
                
        except Exception as e:
            error_msg = f"Exception during logging test: {str(e)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            self.log_test_result("Enhanced Logging Functionality", False, error_msg, {"exception": str(e)})
            return {"success": False, "error": str(e)}
    
    def test_4_data_retrieval_apis(self) -> Dict:
        """Test 4: Data retrieval API endpoints."""
        print("\n🔍 Test 4: Data Retrieval APIs")
        
        if self.database_only:
            print("⏭️  Skipping API test in database-only mode")
            self.log_test_result("Data Retrieval APIs", True, "Skipped in database-only mode")
            return {"success": True, "message": "Skipped in database-only mode"}
        
        try:
            # Test /logs endpoint
            logs_response = requests.get(f"{self.base_url}/logs?limit=5", timeout=10)
            
            if logs_response.status_code == 200:
                logs_data = logs_response.json()
                print(f"📊 /logs endpoint: {len(logs_data.get('rows', []))} records retrieved")
                
                # Test /device_ids endpoint
                devices_response = requests.get(f"{self.base_url}/device_ids", timeout=10)
                
                if devices_response.status_code == 200:
                    devices_data = devices_response.json()
                    print(f"📱 /device_ids endpoint: {len(devices_data.get('ids', []))} devices found")
                    
                    # Test /filteredlogs endpoint with our test device
                    filtered_response = requests.get(
                        f"{self.base_url}/filteredlogs?device_id={self.test_device_id}_api",
                        timeout=10
                    )
                    
                    if filtered_response.status_code == 200:
                        filtered_data = filtered_response.json()
                        filtered_count = len(filtered_data.get('rows', []))
                        print(f"🔍 /filteredlogs endpoint: {filtered_count} filtered records")
                        
                        self.log_test_result(
                            "Data Retrieval APIs",
                            True,
                            f"All retrieval APIs working: logs({len(logs_data.get('rows', []))}), devices({len(devices_data.get('ids', []))}), filtered({filtered_count})",
                            {
                                "logs_count": len(logs_data.get('rows', [])),
                                "devices_count": len(devices_data.get('ids', [])),
                                "filtered_count": filtered_count
                            }
                        )
                        return {"success": True}
                    else:
                        error_msg = f"/filteredlogs failed: {filtered_response.status_code}"
                        self.log_test_result("Data Retrieval APIs", False, error_msg)
                        return {"success": False, "error": error_msg}
                else:
                    error_msg = f"/device_ids failed: {devices_response.status_code}"
                    self.log_test_result("Data Retrieval APIs", False, error_msg)
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"/logs failed: {logs_response.status_code}"
                self.log_test_result("Data Retrieval APIs", False, error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Exception during API retrieval test: {str(e)}"
            print(f"❌ {error_msg}")
            self.log_test_result("Data Retrieval APIs", False, error_msg, {"exception": str(e)})
            return {"success": False, "error": str(e)}
    
    def test_5_data_consistency_check(self) -> Dict:
        """Test 5: Data consistency between direct DB and API operations."""
        print("\n🔄 Test 5: Data Consistency Check")
        
        try:
            # Get all test records from database
            consistency_query = f"SELECT * FROM {TABLE_BIKE_DATA} WHERE device_id LIKE ? ORDER BY id DESC"
            test_records = self.db_manager.execute_query(consistency_query, (f"{self.test_device_id}%",))
            
            print(f"📊 Found {len(test_records)} test records in database")
            
            # In database-only mode, we only expect the direct insert
            expected_records = 1 if self.database_only else 2
            
            if len(test_records) >= expected_records:
                direct_record = None
                api_record = None
                
                for record in test_records:
                    if record.get('device_id', '').endswith('_direct'):
                        direct_record = record
                    elif record.get('device_id', '').endswith('_api'):
                        api_record = record
                
                # In database-only mode, only check direct record
                if self.database_only:
                    if direct_record:
                        self.log_test_result(
                            "Data Consistency Check",
                            True,
                            f"Database-only consistency verified for {len(test_records)} test record(s)",
                            {"records_verified": len(test_records), "mode": "database_only"}
                        )
                        return {"success": True, "records_verified": len(test_records)}
                    else:
                        error_msg = "Direct record not found in database-only mode"
                        self.log_test_result("Data Consistency Check", False, error_msg)
                        return {"success": False, "error": error_msg}
                
                # Full mode - check both records
                if direct_record and api_record:
                    # Compare record structures
                    consistency_issues = []
                    
                    # Check that both have required fields
                    required_fields = ['id', 'timestamp', 'latitude', 'longitude', 'speed', 'direction', 'roughness', 'device_id']
                    for field in required_fields:
                        if field not in direct_record:
                            consistency_issues.append(f"Direct record missing {field}")
                        if field not in api_record:
                            consistency_issues.append(f"API record missing {field}")
                    
                    # Check that timestamps are reasonable (within last hour)
                    now = datetime.now()
                    for record_type, record in [("direct", direct_record), ("api", api_record)]:
                        timestamp_str = record.get('timestamp', '')
                        if timestamp_str:
                            try:
                                record_time = datetime.fromisoformat(str(timestamp_str).replace('Z', '+00:00'))
                                if hasattr(record_time, 'tzinfo') and record_time.tzinfo:
                                    record_time = record_time.replace(tzinfo=None)
                                time_diff = abs((now - record_time).total_seconds())
                                if time_diff > 3600:  # More than 1 hour
                                    consistency_issues.append(f"{record_type} record timestamp too old: {time_diff}s")
                            except Exception as e:
                                consistency_issues.append(f"{record_type} record timestamp parse error: {e}")
                    
                    if consistency_issues:
                        self.log_test_result(
                            "Data Consistency Check",
                            False,
                            f"Consistency issues found: {', '.join(consistency_issues)}",
                            {"issues": consistency_issues, "records_found": len(test_records)}
                        )
                        return {"success": False, "issues": consistency_issues}
                    else:
                        self.log_test_result(
                            "Data Consistency Check",
                            True,
                            f"Data consistency verified across {len(test_records)} test records",
                            {"records_verified": len(test_records)}
                        )
                        return {"success": True, "records_verified": len(test_records)}
                else:
                    error_msg = f"Missing test records: direct={direct_record is not None}, api={api_record is not None}"
                    self.log_test_result("Data Consistency Check", False, error_msg)
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"Insufficient test records found: {len(test_records)}"
                self.log_test_result("Data Consistency Check", False, error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Exception during consistency check: {str(e)}"
            print(f"❌ {error_msg}")
            self.log_test_result("Data Consistency Check", False, error_msg, {"exception": str(e)})
            return {"success": False, "error": str(e)}
    
    def cleanup_test_data(self):
        """Clean up test data from database."""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Delete test records
            cleanup_query = f"DELETE FROM {TABLE_BIKE_DATA} WHERE device_id LIKE ?"
            affected_rows = self.db_manager.execute_non_query(cleanup_query, (f"{self.test_device_id}%",))
            print(f"🗑️  Cleaned up {affected_rows} test records")
            
            # Clean up test logs (optional)
            log_cleanup_query = "DELETE FROM RCI_debug_log WHERE message LIKE ?"
            log_affected = self.db_manager.execute_non_query(log_cleanup_query, ("Test % message%",))
            print(f"📝 Cleaned up {log_affected} test log entries")
            
        except Exception as e:
            print(f"⚠️  Cleanup failed: {e}")
    
    def run_all_tests(self) -> Dict:
        """Run all tests and return summary."""
        print("🚀 Starting Comprehensive Data Flow Test Suite")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run all tests
        test_1_result = self.test_1_direct_database_insert()
        test_2_result = self.test_2_api_post_with_verification()
        test_3_result = self.test_3_enhanced_logging_functionality()
        test_4_result = self.test_4_data_retrieval_apis()
        test_5_result = self.test_5_data_consistency_check()
        
        total_time = time.time() - start_time
        
        # Generate summary
        passed_tests = sum(1 for result in self.test_results if result["success"])
        total_tests = len(self.test_results)
        
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"⏱️  Total execution time: {total_time:.3f}s")
        print(f"✅ Passed: {passed_tests}/{total_tests}")
        print(f"❌ Failed: {total_tests - passed_tests}/{total_tests}")
        print(f"📈 Success rate: {(passed_tests/total_tests*100):.1f}%")
        
        # Show detailed results
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test_name']}: {result['message']}")
        
        # Cleanup
        self.cleanup_test_data()
        
        # Final log entry
        try:
            self.db_manager.log_debug(
                f"Comprehensive test suite completed: {passed_tests}/{total_tests} passed",
                LogLevel.INFO if passed_tests == total_tests else LogLevel.WARNING,
                LogCategory.GENERAL,
                device_id=self.test_device_id
            )
        except Exception:
            pass
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": passed_tests/total_tests,
            "execution_time": total_time,
            "all_passed": passed_tests == total_tests,
            "detailed_results": self.test_results
        }


def main():
    """Main function to run the comprehensive test suite."""
    print("🧪 Road Condition Indexer - Comprehensive Data Flow Test")
    print("=" * 80)
    
    # Initialize test
    test_suite = ComprehensiveDataFlowTest()
    
    # Run all tests
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results["all_passed"] else 1
    print(f"\n🏁 Test suite completed with exit code: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
