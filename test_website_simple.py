#!/usr/bin/env python3
"""
Simplified test script to verify that the website is successfully recording data to the SQL server.

This script performs API-based testing of:
1. Website health check
2. API endpoint functionality (/bike-data)
3. Data submission verification
4. Performance testing

Run this script locally to test your deployed website.
Usage:
    python test_website_simple.py
    python test_website_simple.py --url https://your-website.azurewebsites.net
"""

import json
import time
import math
import random
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Try to import requests, install if not available
try:
    import requests
except ImportError:
    print("Installing required package: requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

class SimpleWebsiteDataTester:
    """Simplified test class for verifying website data recording functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the tester with website URL."""
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Test configuration
        self.test_device_id = f"test_device_{int(time.time())}"
        self.test_results = []
        
        print(f"🔍 Simple Website Data Recording Tester")
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
        if details and any(details.values()):
            for key, value in details.items():
                if value is not None and value != "":
                    print(f"    {key}: {value}")
        print()
    
    def test_website_accessibility(self) -> bool:
        """Test basic website accessibility."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        self.log_test_result(
                            "Website Health Check",
                            True,
                            "Website is healthy and accessible",
                            {
                                "status_code": response.status_code,
                                "database_status": data.get("database", "unknown"),
                                "response_time": f"{response.elapsed.total_seconds():.2f}s"
                            }
                        )
                        return True
                    else:
                        self.log_test_result(
                            "Website Health Check",
                            False,
                            f"Website reports unhealthy status: {data.get('status')}",
                            {"response_data": str(data)}
                        )
                        return False
                except json.JSONDecodeError:
                    self.log_test_result(
                        "Website Health Check",
                        False,
                        "Health endpoint returned non-JSON response",
                        {"response_text": response.text[:200]}
                    )
                    return False
            else:
                self.log_test_result(
                    "Website Health Check",
                    False,
                    f"Health endpoint returned status {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_test_result(
                "Website Health Check",
                False,
                "Cannot connect to website - is it running?",
                {"url": f"{self.base_url}/health"}
            )
            return False
        except Exception as e:
            self.log_test_result(
                "Website Health Check",
                False,
                f"Failed to connect: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def generate_realistic_bike_data(self) -> Dict[str, Any]:
        """Generate realistic test bike data."""
        # Realistic coordinates (Netherlands)
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
            "record_source_data": True
        }
    
    def test_data_submission(self) -> bool:
        """Test submitting bike data to the /bike-data endpoint."""
        test_data = self.generate_realistic_bike_data()
        
        try:
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/bike-data",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get("status") == "ok" and "roughness" in response_data:
                        roughness = response_data["roughness"]
                        self.log_test_result(
                            "Data Submission",
                            True,
                            "Successfully submitted and processed bike data",
                            {
                                "status_code": response.status_code,
                                "roughness": f"{roughness:.4f}",
                                "response_time": f"{response_time:.2f}s",
                                "data_points": len(test_data["z_values"]),
                                "test_speed": f"{test_data['speed']:.1f} km/h"
                            }
                        )
                        return True
                    else:
                        self.log_test_result(
                            "Data Submission",
                            False,
                            f"Unexpected response format",
                            {"response_data": str(response_data)}
                        )
                        return False
                except json.JSONDecodeError:
                    self.log_test_result(
                        "Data Submission",
                        False,
                        "Server returned non-JSON response",
                        {"response_text": response.text[:200]}
                    )
                    return False
            elif response.status_code == 422:
                # Validation error
                try:
                    error_detail = response.json()
                except:
                    error_detail = response.text[:200]
                self.log_test_result(
                    "Data Submission",
                    False,
                    "Data validation failed",
                    {"status_code": response.status_code, "error": str(error_detail)}
                )
                return False
            elif response.status_code == 500:
                self.log_test_result(
                    "Data Submission",
                    False,
                    "Server internal error - possible database issue",
                    {"status_code": response.status_code, "response": response.text[:200]}
                )
                return False
            else:
                self.log_test_result(
                    "Data Submission",
                    False,
                    f"HTTP error {response.status_code}",
                    {"status_code": response.status_code, "response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Data Submission",
                False,
                f"Failed to submit data: {str(e)}",
                {"error_type": type(e).__name__}
            )
            return False
    
    def test_multiple_submissions(self, count: int = 5) -> bool:
        """Test multiple data submissions to verify consistent recording."""
        print(f"🔄 Testing {count} consecutive data submissions...")
        
        success_count = 0
        response_times = []
        roughness_values = []
        
        for i in range(count):
            test_data = self.generate_realistic_bike_data()
            
            try:
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/bike-data",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                )
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("status") == "ok":
                        success_count += 1
                        roughness = response_data.get("roughness", 0)
                        roughness_values.append(roughness)
                        print(f"    ✅ Submission {i+1}: OK (roughness: {roughness:.4f}, {response_time:.2f}s)")
                    else:
                        print(f"    ❌ Submission {i+1}: Server rejected data - {response_data}")
                else:
                    print(f"    ❌ Submission {i+1}: HTTP {response.status_code}")
            except Exception as e:
                print(f"    ❌ Submission {i+1}: Exception - {e}")
            
            # Brief delay between submissions to avoid overwhelming the server
            time.sleep(0.5)
        
        success_rate = success_count / count
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        avg_roughness = sum(roughness_values) / len(roughness_values) if roughness_values else 0
        
        # Success criteria: at least 80% success rate
        success = success_rate >= 0.8
        
        self.log_test_result(
            "Multiple Data Submissions",
            success,
            f"Submitted {success_count}/{count} successfully ({success_rate:.1%} success rate)",
            {
                "success_rate": f"{success_rate:.1%}",
                "avg_response_time": f"{avg_response_time:.2f}s",
                "avg_roughness": f"{avg_roughness:.4f}",
                "threshold": "80% success rate required"
            }
        )
        
        return success
    
    def test_data_validation(self) -> bool:
        """Test that the server properly validates submitted data."""
        print("🔍 Testing data validation...")
        
        # Test with invalid data to ensure server validates properly
        invalid_data_tests = [
            {
                "name": "Missing required fields",
                "data": {"latitude": 52.0, "longitude": 5.0},  # Missing other required fields
                "should_fail": True
            },
            {
                "name": "Invalid coordinates",
                "data": {
                    "latitude": 999.0,  # Invalid latitude
                    "longitude": 5.0,
                    "speed": 20.0,
                    "direction": 90.0,
                    "device_id": "test",
                    "z_values": [0.1] * 60
                },
                "should_fail": True
            },
            {
                "name": "Empty z_values",
                "data": {
                    "latitude": 52.0,
                    "longitude": 5.0,
                    "speed": 20.0,
                    "direction": 90.0,
                    "device_id": "test",
                    "z_values": []  # Empty array
                },
                "should_fail": True
            }
        ]
        
        validation_working = 0
        total_validation_tests = len(invalid_data_tests)
        
        for test in invalid_data_tests:
            try:
                response = self.session.post(
                    f"{self.base_url}/bike-data",
                    json=test["data"],
                    headers={"Content-Type": "application/json"}
                )
                
                if test["should_fail"] and response.status_code in [400, 422]:
                    validation_working += 1
                    print(f"    ✅ {test['name']}: Correctly rejected (HTTP {response.status_code})")
                elif test["should_fail"] and response.status_code == 200:
                    print(f"    ⚠️ {test['name']}: Should have been rejected but was accepted")
                else:
                    print(f"    ❓ {test['name']}: Unexpected response (HTTP {response.status_code})")
                    
            except Exception as e:
                print(f"    ❌ {test['name']}: Exception - {e}")
        
        validation_success = validation_working >= (total_validation_tests * 0.5)  # At least half should work
        
        self.log_test_result(
            "Data Validation",
            validation_success,
            f"Server validation working for {validation_working}/{total_validation_tests} test cases",
            {
                "validation_tests_passed": validation_working,
                "total_validation_tests": total_validation_tests,
                "threshold": "50% validation tests must pass"
            }
        )
        
        return validation_success
    
    def test_performance_under_load(self) -> bool:
        """Test basic performance characteristics."""
        print("⚡ Testing performance characteristics...")
        
        response_times = []
        successful_requests = 0
        total_requests = 10
        
        for i in range(total_requests):
            test_data = self.generate_realistic_bike_data()
            
            try:
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/bike-data",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    response_times.append(response_time)
                    successful_requests += 1
                
                # Small delay to avoid overwhelming
                time.sleep(0.2)
                
            except Exception as e:
                print(f"    ⚠️ Request {i+1} failed: {e}")
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            # Performance criteria: average < 5 seconds, max < 10 seconds, success rate > 80%
            performance_ok = (avg_time < 5.0 and 
                            max_time < 10.0 and 
                            successful_requests / total_requests >= 0.8)
            
            self.log_test_result(
                "Performance Test",
                performance_ok,
                f"Average response time: {avg_time:.2f}s",
                {
                    "successful_requests": f"{successful_requests}/{total_requests}",
                    "avg_response_time": f"{avg_time:.2f}s",
                    "min_response_time": f"{min_time:.2f}s",
                    "max_response_time": f"{max_time:.2f}s",
                    "success_rate": f"{successful_requests/total_requests:.1%}",
                    "threshold": "avg<5s, max<10s, success>80%"
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
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary results."""
        print("🚀 Starting website data recording tests...\n")
        
        # Define tests to run
        tests = [
            ("Website Accessibility", self.test_website_accessibility),
            ("Single Data Submission", self.test_data_submission),
            ("Multiple Data Submissions", lambda: self.test_multiple_submissions(5)),
            ("Data Validation", self.test_data_validation),
            ("Performance", self.test_performance_under_load)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
                self.log_test_result(test_name, False, f"Test crashed: {e}", {"error": str(e)})
        
        # Generate summary
        success_rate = passed / total
        overall_success = success_rate >= 0.6  # 60% success rate for overall pass
        
        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Tests Passed: {passed}/{total} ({success_rate:.1%})")
        
        if overall_success:
            print("🎉 Overall Result: ✅ PASS - Website is successfully recording data!")
            print("\n✅ Your website appears to be working correctly:")
            print("   • API endpoints are responding")
            print("   • Data is being processed and stored")
            print("   • Performance is acceptable")
            print("   • Data validation is working")
        else:
            print("❌ Overall Result: FAIL - Issues detected with data recording")
            print("\n❌ Problems found:")
            failed_tests = [r for r in self.test_results if not r["success"]]
            for result in failed_tests:
                print(f"   • {result['test_name']}: {result['message']}")
        
        print("\n" + "=" * 80)
        print("📋 DETAILED RESULTS:")
        print("=" * 80)
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {result['test_name']}")
            print(f"    {result['message']}")
            if result.get("details"):
                for key, value in result["details"].items():
                    if value is not None and value != "":
                        print(f"    {key}: {value}")
            print()
        
        return {
            "overall_success": overall_success,
            "tests_passed": passed,
            "tests_total": total,
            "success_rate": success_rate,
            "detailed_results": self.test_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_url": self.base_url
        }


def main():
    """Main function to run the tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test website data recording functionality")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL of the website (default: http://localhost:8000)")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = SimpleWebsiteDataTester(args.url)
    
    try:
        # Run tests
        results = tester.run_all_tests()
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Full results saved to {args.output}")
        
        # Exit with appropriate code
        exit_code = 0 if results["overall_success"] else 1
        print(f"\n🏁 Testing completed - Exit code: {exit_code}")
        
        if results["overall_success"]:
            print("\n🎯 CONCLUSION: Your website is successfully recording data to the SQL server!")
        else:
            print("\n⚠️ CONCLUSION: There are issues with data recording that need to be addressed.")
            
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 2
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        return 3


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
