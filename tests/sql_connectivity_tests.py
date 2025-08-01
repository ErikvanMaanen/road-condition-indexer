"""
SQL Connectivity Test Module for Road Condition Indexer

This module provides comprehensive SQL Server connectivity testing for both local 
development (using .env file) and Azure App Service deployment (using app settings).

Features:
- Environment variable loading with fallback
- Connection timeout and retry logic
- Comprehensive connectivity tests
- Performance benchmarking
- Detailed logging and reporting
"""

import os
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pymssql
import socket

# Try to import python-dotenv for local development
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from log_utils import LogLevel, LogCategory, log_info, log_warning, log_error, log_debug


class ConnectivityTestResult(Enum):
    """Enumeration for connectivity test results."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    WARNING = "WARNING"
    TIMEOUT = "TIMEOUT"
    DNS_ERROR = "DNS_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"


@dataclass
class TestResult:
    """Data class for individual test results."""
    test_name: str
    result: ConnectivityTestResult
    duration_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ConnectivityReport:
    """Data class for complete connectivity test report."""
    overall_status: ConnectivityTestResult
    total_duration_ms: float
    tests: List[TestResult]
    environment_info: Dict[str, str]
    recommendations: List[str]


class SQLConnectivityTester:
    """
    Comprehensive SQL Server connectivity tester with Azure App Service support.
    
    This class provides:
    - Environment variable detection and loading
    - Progressive connectivity testing
    - Performance benchmarking
    - Detailed error reporting with recommendations
    """
    
    def __init__(self, timeout_seconds: int = 30, retry_attempts: int = 3):
        """
        Initialize the SQL connectivity tester.
        
        Args:
            timeout_seconds: Connection timeout in seconds
            retry_attempts: Number of retry attempts for failed connections
        """
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.environment_vars = self._load_environment_variables()
        
    def _load_environment_variables(self) -> Dict[str, str]:
        """
        Load environment variables with support for both .env files and Azure App Service.
        
        Priority order:
        1. Azure App Service environment variables (production)
        2. Local .env file (development)
        3. System environment variables (fallback)
        
        Returns:
            Dictionary containing loaded environment variables
        """
        env_vars = {}
        
        # Check if we're running in Azure App Service
        is_azure_app_service = bool(os.getenv('WEBSITE_SITE_NAME'))
        
        if is_azure_app_service:
            log_info("🌐 Detected Azure App Service environment", LogCategory.STARTUP)
        else:
            log_info("🏠 Detected local development environment", LogCategory.STARTUP)
            # Try to load .env file for local development
            env_file_path = Path(__file__).parent / ".env"
            
            if DOTENV_AVAILABLE and env_file_path.exists():
                log_info(f"📁 Loading environment from: {env_file_path}", LogCategory.STARTUP)
                try:
                    from dotenv import load_dotenv
                    load_dotenv(env_file_path)
                except Exception as e:
                    log_warning(f"⚠️ Failed to load .env file: {e}", LogCategory.STARTUP)
            elif env_file_path.exists() and not DOTENV_AVAILABLE:
                log_warning("⚠️ .env file found but python-dotenv not installed", LogCategory.STARTUP)
                log_warning("💡 Install with: pip install python-dotenv", LogCategory.STARTUP)
            else:
                log_info("📋 No .env file found, using system environment variables", LogCategory.STARTUP)
        
        # Load variables from environment (after potential .env loading)
        required_vars = [
            "AZURE_SQL_SERVER", "AZURE_SQL_PORT", "AZURE_SQL_USER", 
            "AZURE_SQL_PASSWORD", "AZURE_SQL_DATABASE"
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                env_vars[var] = value
            elif not is_azure_app_service:
                # Only log warnings for local development
                log_warning(f"⚠️ Missing environment variable: {var}", LogCategory.STARTUP)
        
        # Log loaded variables (without sensitive data)
        log_info(f"🔧 Loaded {len(env_vars)} environment variables", LogCategory.STARTUP)
        safe_vars = {k: "***" if "PASSWORD" in k or "SECRET" in k else v 
                    for k, v in env_vars.items()}
        # Use log_info instead of log_debug to avoid parameter mismatch
        log_info(f"Environment variables: {safe_vars}", LogCategory.STARTUP)
        
        return env_vars
    
    def _validate_environment(self) -> TestResult:
        """
        Validate that all required environment variables are present.
        
        Returns:
            TestResult for environment validation
        """
        start_time = time.time()
        required_vars = [
            "AZURE_SQL_SERVER", "AZURE_SQL_PORT", "AZURE_SQL_USER", 
            "AZURE_SQL_PASSWORD", "AZURE_SQL_DATABASE"
        ]
        
        missing_vars = [var for var in required_vars if var not in self.environment_vars]
        duration_ms = (time.time() - start_time) * 1000
        
        if missing_vars:
            return TestResult(
                test_name="Environment Validation",
                result=ConnectivityTestResult.FAILED,
                duration_ms=duration_ms,
                message=f"Missing required environment variables: {', '.join(missing_vars)}",
                details={"missing_variables": missing_vars, "available_variables": list(self.environment_vars.keys())}
            )
        
        return TestResult(
            test_name="Environment Validation",
            result=ConnectivityTestResult.SUCCESS,
            duration_ms=duration_ms,
            message="All required environment variables are present",
            details={"validated_variables": required_vars}
        )
    
    def _test_dns_resolution(self) -> TestResult:
        """
        Test DNS resolution for the SQL Server hostname.
        
        Returns:
            TestResult for DNS resolution test
        """
        start_time = time.time()
        server_name = self.environment_vars.get("AZURE_SQL_SERVER", "")
        
        if not server_name:
            return TestResult(
                test_name="DNS Resolution",
                result=ConnectivityTestResult.FAILED,
                duration_ms=0,
                message="No server name provided for DNS resolution"
            )
        
        try:
            # Remove .database.windows.net if present and resolve
            hostname = server_name.replace(".database.windows.net", "") + ".database.windows.net"
            ip_address = socket.gethostbyname(hostname)
            duration_ms = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name="DNS Resolution",
                result=ConnectivityTestResult.SUCCESS,
                duration_ms=duration_ms,
                message=f"Successfully resolved {hostname} to {ip_address}",
                details={"hostname": hostname, "ip_address": ip_address}
            )
            
        except socket.gaierror as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name="DNS Resolution",
                result=ConnectivityTestResult.DNS_ERROR,
                duration_ms=duration_ms,
                message=f"DNS resolution failed: {str(e)}",
                details={"hostname": server_name, "error": str(e)}
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name="DNS Resolution",
                result=ConnectivityTestResult.FAILED,
                duration_ms=duration_ms,
                message=f"Unexpected error during DNS resolution: {str(e)}"
            )
    
    def _test_port_connectivity(self) -> TestResult:
        """
        Test TCP connectivity to the SQL Server port.
        
        Returns:
            TestResult for port connectivity test
        """
        start_time = time.time()
        server_name = self.environment_vars.get("AZURE_SQL_SERVER", "")
        port = int(self.environment_vars.get("AZURE_SQL_PORT", "1433"))
        
        if not server_name:
            return TestResult(
                test_name="Port Connectivity",
                result=ConnectivityTestResult.FAILED,
                duration_ms=0,
                message="No server name provided for port connectivity test"
            )
        
        try:
            # Remove .database.windows.net if present
            hostname = server_name.replace(".database.windows.net", "") + ".database.windows.net"
            
            with socket.create_connection((hostname, port), timeout=self.timeout_seconds) as sock:
                duration_ms = (time.time() - start_time) * 1000
                return TestResult(
                    test_name="Port Connectivity",
                    result=ConnectivityTestResult.SUCCESS,
                    duration_ms=duration_ms,
                    message=f"Successfully connected to {hostname}:{port}",
                    details={"hostname": hostname, "port": port}
                )
                
        except socket.timeout:
            duration_ms = (time.time() - start_time) * 1000
            hostname = server_name.replace(".database.windows.net", "") + ".database.windows.net"
            return TestResult(
                test_name="Port Connectivity",
                result=ConnectivityTestResult.TIMEOUT,
                duration_ms=duration_ms,
                message=f"Connection timeout after {self.timeout_seconds} seconds",
                details={"hostname": hostname, "port": port, "timeout": self.timeout_seconds}
            )
        except ConnectionRefusedError:
            duration_ms = (time.time() - start_time) * 1000
            hostname = server_name.replace(".database.windows.net", "") + ".database.windows.net"
            return TestResult(
                test_name="Port Connectivity",
                result=ConnectivityTestResult.CONNECTION_ERROR,
                duration_ms=duration_ms,
                message=f"Connection refused to {hostname}:{port}",
                details={"hostname": hostname, "port": port}
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name="Port Connectivity",
                result=ConnectivityTestResult.FAILED,
                duration_ms=duration_ms,
                message=f"Port connectivity failed: {str(e)}"
            )
    
    def _test_authentication(self) -> TestResult:
        """
        Test SQL Server authentication with retry logic.
        
        Returns:
            TestResult for authentication test
        """
        start_time = time.time()
        
        server = self.environment_vars.get("AZURE_SQL_SERVER", "")
        database = self.environment_vars.get("AZURE_SQL_DATABASE", "")
        user = self.environment_vars.get("AZURE_SQL_USER", "")
        password = self.environment_vars.get("AZURE_SQL_PASSWORD", "")
        port = int(self.environment_vars.get("AZURE_SQL_PORT", "1433"))
        
        # Ensure server has proper suffix
        if not server.endswith(".database.windows.net"):
            server = server + ".database.windows.net"
        
        for attempt in range(self.retry_attempts):
            try:
                conn = pymssql.connect(
                    server=server,
                    user=user,
                    password=password,
                    database=database,
                    port=str(port),
                    timeout=self.timeout_seconds,
                    login_timeout=self.timeout_seconds
                )
                
                with conn:
                    duration_ms = (time.time() - start_time) * 1000
                    return TestResult(
                        test_name="Authentication",
                        result=ConnectivityTestResult.SUCCESS,
                        duration_ms=duration_ms,
                        message=f"Successfully authenticated to database '{database}'",
                        details={
                            "server": server, 
                            "database": database, 
                            "user": user,
                            "attempt": attempt + 1
                        }
                    )
                    
            except pymssql.OperationalError as e:
                error_message = str(e)
                if "Login failed" in error_message or "authentication" in error_message.lower():
                    duration_ms = (time.time() - start_time) * 1000
                    return TestResult(
                        test_name="Authentication",
                        result=ConnectivityTestResult.AUTH_ERROR,
                        duration_ms=duration_ms,
                        message=f"Authentication failed: {error_message}",
                        details={"server": server, "database": database, "user": user}
                    )
                elif attempt < self.retry_attempts - 1:
                    log_warning(f"⚠️ Authentication attempt {attempt + 1} failed, retrying...", LogCategory.STARTUP)
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    duration_ms = (time.time() - start_time) * 1000
                    return TestResult(
                        test_name="Authentication",
                        result=ConnectivityTestResult.FAILED,
                        duration_ms=duration_ms,
                        message=f"Authentication failed after {self.retry_attempts} attempts: {error_message}"
                    )
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    log_warning(f"⚠️ Authentication attempt {attempt + 1} failed, retrying...", LogCategory.STARTUP)
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    duration_ms = (time.time() - start_time) * 1000
                    return TestResult(
                        test_name="Authentication",
                        result=ConnectivityTestResult.FAILED,
                        duration_ms=duration_ms,
                        message=f"Authentication failed: {str(e)}"
                    )
        
        # This should never be reached, but just in case
        duration_ms = (time.time() - start_time) * 1000
        return TestResult(
            test_name="Authentication",
            result=ConnectivityTestResult.FAILED,
            duration_ms=duration_ms,
            message="Authentication failed: Unexpected error"
        )
    
    def _test_query_execution(self) -> TestResult:
        """
        Test basic SQL query execution.
        
        Returns:
            TestResult for query execution test
        """
        start_time = time.time()
        
        server = self.environment_vars.get("AZURE_SQL_SERVER", "")
        database = self.environment_vars.get("AZURE_SQL_DATABASE", "")
        user = self.environment_vars.get("AZURE_SQL_USER", "")
        password = self.environment_vars.get("AZURE_SQL_PASSWORD", "")
        port = int(self.environment_vars.get("AZURE_SQL_PORT", "1433"))
        
        # Ensure server has proper suffix
        if not server.endswith(".database.windows.net"):
            server = server + ".database.windows.net"
        
        try:
            conn = pymssql.connect(
                server=server,
                user=user,
                password=password,
                database=database,
                port=str(port),
                timeout=self.timeout_seconds,
                login_timeout=self.timeout_seconds
            )
            
            with conn:
                cursor = conn.cursor()
                
                # Test basic query
                cursor.execute("SELECT 1 as test_value, GETDATE() as server_time")
                result = cursor.fetchone()
                
                # Test database-specific query
                cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_type = 'BASE TABLE'")
                table_count_result = cursor.fetchone()
                table_count = table_count_result[0] if table_count_result else 0
                
                duration_ms = (time.time() - start_time) * 1000
                return TestResult(
                    test_name="Query Execution",
                    result=ConnectivityTestResult.SUCCESS,
                    duration_ms=duration_ms,
                    message=f"Successfully executed queries. Database has {table_count} tables.",
                    details={
                        "test_value": result[0] if result else None,
                        "server_time": str(result[1]) if result else None,
                        "table_count": table_count
                    }
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name="Query Execution",
                result=ConnectivityTestResult.FAILED,
                duration_ms=duration_ms,
                message=f"Query execution failed: {str(e)}"
            )
    
    def _benchmark_performance(self) -> TestResult:
        """
        Run performance benchmark tests.
        
        Returns:
            TestResult for performance benchmark
        """
        start_time = time.time()
        
        server = self.environment_vars.get("AZURE_SQL_SERVER", "")
        database = self.environment_vars.get("AZURE_SQL_DATABASE", "")
        user = self.environment_vars.get("AZURE_SQL_USER", "")
        password = self.environment_vars.get("AZURE_SQL_PASSWORD", "")
        port = int(self.environment_vars.get("AZURE_SQL_PORT", "1433"))
        
        # Ensure server has proper suffix
        if not server.endswith(".database.windows.net"):
            server = server + ".database.windows.net"
        
        try:
            # Connection time benchmark
            conn_start = time.time()
            conn = pymssql.connect(
                server=server,
                user=user,
                password=password,
                database=database,
                port=str(port),
                timeout=self.timeout_seconds,
                login_timeout=self.timeout_seconds
            )
            connection_time_ms = (time.time() - conn_start) * 1000
            
            with conn:
                cursor = conn.cursor()
                
                # Query execution time benchmark
                query_times = []
                for i in range(5):  # Run 5 test queries
                    query_start = time.time()
                    cursor.execute("SELECT COUNT(*) FROM information_schema.columns")
                    cursor.fetchone()
                    query_times.append((time.time() - query_start) * 1000)
                
                avg_query_time_ms = sum(query_times) / len(query_times)
                max_query_time_ms = max(query_times)
                min_query_time_ms = min(query_times)
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Determine performance rating
                if connection_time_ms < 1000 and avg_query_time_ms < 100:
                    result_status = ConnectivityTestResult.SUCCESS
                    message = "Excellent performance"
                elif connection_time_ms < 3000 and avg_query_time_ms < 500:
                    result_status = ConnectivityTestResult.SUCCESS
                    message = "Good performance"
                elif connection_time_ms < 10000 and avg_query_time_ms < 1000:
                    result_status = ConnectivityTestResult.WARNING
                    message = "Acceptable performance"
                else:
                    result_status = ConnectivityTestResult.WARNING
                    message = "Slow performance detected"
                
                return TestResult(
                    test_name="Performance Benchmark",
                    result=result_status,
                    duration_ms=duration_ms,
                    message=f"{message} - Conn: {connection_time_ms:.1f}ms, Avg Query: {avg_query_time_ms:.1f}ms",
                    details={
                        "connection_time_ms": round(connection_time_ms, 2),
                        "avg_query_time_ms": round(avg_query_time_ms, 2),
                        "min_query_time_ms": round(min_query_time_ms, 2),
                        "max_query_time_ms": round(max_query_time_ms, 2),
                        "query_samples": len(query_times)
                    }
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name="Performance Benchmark",
                result=ConnectivityTestResult.FAILED,
                duration_ms=duration_ms,
                message=f"Performance benchmark failed: {str(e)}"
            )
    
    def run_comprehensive_tests(self) -> ConnectivityReport:
        """
        Run all connectivity tests and return a comprehensive report.
        
        Returns:
            ConnectivityReport with all test results and recommendations
        """
        test_start_time = time.time()
        log_info("🧪 Starting comprehensive SQL connectivity tests...", LogCategory.STARTUP)
        
        # Run all tests in sequence
        tests = [
            self._validate_environment(),
            self._test_dns_resolution(),
            self._test_port_connectivity(),
            self._test_authentication(),
            self._test_query_execution(),
            self._benchmark_performance()
        ]
        
        # Determine overall status
        failed_tests = [t for t in tests if t.result == ConnectivityTestResult.FAILED]
        auth_errors = [t for t in tests if t.result == ConnectivityTestResult.AUTH_ERROR]
        warning_tests = [t for t in tests if t.result == ConnectivityTestResult.WARNING]
        
        if failed_tests or auth_errors:
            overall_status = ConnectivityTestResult.FAILED
        elif warning_tests:
            overall_status = ConnectivityTestResult.WARNING
        else:
            overall_status = ConnectivityTestResult.SUCCESS
        
        # Generate recommendations
        recommendations = self._generate_recommendations(tests)
        
        # Gather environment info
        environment_info = {
            "is_azure_app_service": str(bool(os.getenv('WEBSITE_SITE_NAME'))),
            "python_version": sys.version,
            "server": self.environment_vars.get("AZURE_SQL_SERVER", "N/A"),
            "database": self.environment_vars.get("AZURE_SQL_DATABASE", "N/A"),
            "port": self.environment_vars.get("AZURE_SQL_PORT", "N/A"),
            "timeout_seconds": str(self.timeout_seconds),
            "retry_attempts": str(self.retry_attempts)
        }
        
        total_duration_ms = (time.time() - test_start_time) * 1000
        
        report = ConnectivityReport(
            overall_status=overall_status,
            total_duration_ms=total_duration_ms,
            tests=tests,
            environment_info=environment_info,
            recommendations=recommendations
        )
        
        self._log_test_results(report)
        return report
    
    def _generate_recommendations(self, tests: List[TestResult]) -> List[str]:
        """
        Generate recommendations based on test results.
        
        Args:
            tests: List of test results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check for specific issues and provide recommendations
        for test in tests:
            if test.result == ConnectivityTestResult.FAILED:
                if test.test_name == "Environment Validation":
                    recommendations.append(
                        "🔧 Set missing environment variables in Azure App Service Configuration or local .env file"
                    )
                elif test.test_name == "DNS Resolution":
                    recommendations.append(
                        "🌐 Verify SQL Server hostname is correct and network connectivity is available"
                    )
                elif test.test_name == "Port Connectivity":
                    recommendations.append(
                        "🔌 Check firewall rules and ensure port 1433 is accessible from your network"
                    )
                elif test.test_name == "Authentication":
                    recommendations.append(
                        "🔑 Verify username/password and ensure user has proper permissions on the database"
                    )
                elif test.test_name == "Query Execution":
                    recommendations.append(
                        "💾 Check database permissions and ensure the database exists and is accessible"
                    )
            
            elif test.result == ConnectivityTestResult.AUTH_ERROR:
                recommendations.append(
                    "🚫 Authentication failed - verify credentials and user permissions"
                )
            
            elif test.result == ConnectivityTestResult.WARNING:
                if test.test_name == "Performance Benchmark":
                    recommendations.append(
                        "⚡ Consider upgrading SQL Server tier or optimizing network connectivity for better performance"
                    )
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ All tests passed - SQL connectivity is working properly")
        
        # Add environment-specific recommendations
        is_azure = bool(os.getenv('WEBSITE_SITE_NAME'))
        if not is_azure and DOTENV_AVAILABLE:
            recommendations.append("💡 For local development, ensure your .env file contains all required variables")
        elif not is_azure and not DOTENV_AVAILABLE:
            recommendations.append("💡 Install python-dotenv for easier local development: pip install python-dotenv")
        
        return recommendations
    
    def _log_test_results(self, report: ConnectivityReport) -> None:
        """
        Log comprehensive test results.
        
        Args:
            report: ConnectivityReport to log
        """
        # Log overall result
        if report.overall_status == ConnectivityTestResult.SUCCESS:
            log_info(f"✅ SQL connectivity tests completed successfully in {report.total_duration_ms:.1f}ms", 
                    LogCategory.STARTUP)
        elif report.overall_status == ConnectivityTestResult.WARNING:
            log_warning(f"⚠️ SQL connectivity tests completed with warnings in {report.total_duration_ms:.1f}ms", 
                       LogCategory.STARTUP)
        else:
            log_error(f"❌ SQL connectivity tests failed in {report.total_duration_ms:.1f}ms", 
                     LogCategory.STARTUP)
        
        # Log individual test results
        for test in report.tests:
            status_emoji = {
                ConnectivityTestResult.SUCCESS: "✅",
                ConnectivityTestResult.WARNING: "⚠️",
                ConnectivityTestResult.FAILED: "❌",
                ConnectivityTestResult.TIMEOUT: "⏱️",
                ConnectivityTestResult.DNS_ERROR: "🌐",
                ConnectivityTestResult.AUTH_ERROR: "🔑",
                ConnectivityTestResult.CONNECTION_ERROR: "🔌"
            }.get(test.result, "❓")
            
            log_level = LogLevel.INFO if test.result == ConnectivityTestResult.SUCCESS else \
                       LogLevel.WARNING if test.result == ConnectivityTestResult.WARNING else \
                       LogLevel.ERROR
            
            message = f"{status_emoji} {test.test_name}: {test.message} ({test.duration_ms:.1f}ms)"
            
            if log_level == LogLevel.INFO:
                log_info(message, LogCategory.STARTUP)
            elif log_level == LogLevel.WARNING:
                log_warning(message, LogCategory.STARTUP)
            else:
                log_error(message, LogCategory.STARTUP)
        
        # Log recommendations
        if report.recommendations:
            log_info("💡 Recommendations:", LogCategory.STARTUP)
            for recommendation in report.recommendations:
                log_info(f"   {recommendation}", LogCategory.STARTUP)


def run_startup_connectivity_tests(timeout_seconds: int = 30, retry_attempts: int = 3) -> ConnectivityReport:
    """
    Convenience function to run SQL connectivity tests during application startup.
    
    Args:
        timeout_seconds: Connection timeout in seconds
        retry_attempts: Number of retry attempts for failed connections
        
    Returns:
        ConnectivityReport with test results
        
    Raises:
        RuntimeError: If critical connectivity tests fail
    """
    try:
        tester = SQLConnectivityTester(timeout_seconds=timeout_seconds, retry_attempts=retry_attempts)
        report = tester.run_comprehensive_tests()
        
        # Fail fast if critical tests failed
        if report.overall_status == ConnectivityTestResult.FAILED:
            critical_failures = [t for t in report.tests 
                               if t.result in [ConnectivityTestResult.FAILED, ConnectivityTestResult.AUTH_ERROR]
                               and t.test_name in ["Environment Validation", "Authentication"]]
            
            if critical_failures:
                error_messages = [f"{t.test_name}: {t.message}" for t in critical_failures]
                raise RuntimeError(f"Critical SQL connectivity failures detected: {'; '.join(error_messages)}")
        
        return report
        
    except Exception as e:
        log_error(f"❌ SQL connectivity testing failed: {str(e)}", LogCategory.STARTUP)
        raise


# Export main classes and functions
__all__ = [
    'SQLConnectivityTester',
    'ConnectivityTestResult', 
    'TestResult',
    'ConnectivityReport',
    'run_startup_connectivity_tests'
]
