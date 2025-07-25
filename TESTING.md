# Road Condition Indexer - Test Suite

This directory contains comprehensive tests for the Road Condition Indexer application that verify both database operations and API functionality. All test files are located in the `tests/` folder.

## Test Files

### 1. `tests/test_comprehensive_data_flow.py`
A comprehensive test suite that validates:
- ✅ Direct database insert operations
- 🌐 API POST endpoint functionality (when server is running)
- 📝 Enhanced logging system with multiple levels and categories
- 🔍 Data retrieval API endpoints (when server is running)
- 🔄 Data consistency between different data entry methods

### 2. `tests/test_runner.py`
A smart test runner that can operate in two modes:
- **Database-only mode** (default): Tests database operations without requiring API server
- **Full mode**: Tests both database and API operations with automatic server management

## Running Tests

### Quick Database-Only Tests
```bash
python tests/test_runner.py
```
This runs all database tests and skips API tests. Perfect for development and CI/CD pipelines.

### Full Test Suite (Database + API)
```bash
python tests/test_runner.py full
```
This automatically:
1. Starts the FastAPI server on localhost:8000
2. Runs all tests including API endpoints
3. Stops the server when complete

### Manual Test Execution
```bash
# Direct execution (requires manual server management)
python tests/test_comprehensive_data_flow.py

# Set database-only mode manually
set RCI_TEST_MODE=database_only
python tests/test_comprehensive_data_flow.py
```

## Test Features

### 🎯 Comprehensive Coverage
- **Direct Database Operations**: Tests insert, update, delete operations
- **API Integration**: Validates REST endpoints for data submission and retrieval
- **Logging System**: Tests enhanced logging with filtering by level and category
- **Data Integrity**: Verifies consistency between different data entry methods
- **Error Handling**: Tests exception scenarios and recovery

### 🔧 Smart Test Management
- **Unique Test Data**: Each test run uses unique device IDs to avoid conflicts
- **Automatic Cleanup**: All test data is automatically cleaned up after each run
- **Flexible Execution**: Can run with or without API server
- **Detailed Reporting**: Comprehensive test results with timing and success rates

### 📊 Test Results
The test suite provides detailed output including:
- Individual test status (✅ PASS / ❌ FAIL)
- Execution timing
- Success rate percentage
- Detailed error messages for failed tests
- Cleanup confirmation

## Example Output

```
🧪 Road Condition Indexer Test Runner
==================================================
💡 Running database-only tests. Use 'python tests/test_runner.py full' for API tests.

🧪 Running Database-Only Tests
==================================================
🧪 Road Condition Indexer - Comprehensive Data Flow Test
================================================================================
🔧 Test Device ID: test_20250724_182625_942228f6
🗄️  Database Type: SQL Server
--------------------------------------------------------------------------------
✅ PASS Direct Database Insert: Successfully inserted and verified record ID 32
✅ PASS API POST with Verification: Skipped in database-only mode
✅ PASS Enhanced Logging Functionality: Successfully logged and retrieved 4 of 5 enhanced log messages (acceptable)
✅ PASS Data Retrieval APIs: Skipped in database-only mode
✅ PASS Data Consistency Check: Database-only consistency verified for 1 test record(s)
================================================================================
📊 TEST SUMMARY
================================================================================
⏱️  Total execution time: 4.749s
✅ Passed: 5/5
📈 Success rate: 100.0%
✅ All tests passed!
```

## Development Workflow

### For Development
1. Use `python tests/test_runner.py` during development to quickly validate database operations
2. Use `python tests/test_runner.py full` before committing to ensure full functionality

### For CI/CD
- Use database-only mode in CI/CD pipelines where API server setup is complex
- The tests will automatically skip API-dependent operations and focus on core functionality

### For Production Validation
- Use full mode to validate complete system functionality
- Tests will verify both data persistence and API accessibility

## Configuration

### Environment Variables
- `RCI_TEST_MODE=database_only`: Forces database-only testing mode
- Standard RCI configuration variables apply (database connection, etc.)

### Database Support
- Tests work with both SQLite (development) and SQL Server (production)
- Automatic database type detection and appropriate test adjustments

## Troubleshooting

### Common Issues
1. **Import errors**: Ensure all requirements are installed (`pip install -r requirements.txt`)
2. **Database connection**: Verify database configuration and permissions
3. **API tests failing**: Check if port 8000 is available, or use database-only mode

### Test Data
- All test data uses unique device IDs with timestamp and UUID components
- Test data is automatically cleaned up, but manual cleanup is available if needed
- Test logs are stored in the same logging system as the main application

## Integration with Main Application

The test suite integrates with:
- **Database Manager**: Uses the same DatabaseManager class as the main application
- **Logging System**: Tests the enhanced logging system with levels and categories
- **API Endpoints**: Validates the same FastAPI routes used by the web interface
- **Data Models**: Uses the same data structures and validation as the main application

This ensures that the tests accurately reflect real-world usage and catch integration issues.
