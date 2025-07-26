# Website Data Recording Test Scripts

This directory contains test scripts to verify that your Road Condition Indexer website is successfully recording data to the SQL server.

## Quick Start

### Option 1: Using the Batch File (Windows)
Simply double-click `run_website_test.bat` or run from command prompt:
```bash
run_website_test.bat
```

To test a remote website:
```bash
run_website_test.bat https://your-website.azurewebsites.net
```

### Option 2: Using Python Directly
```bash
# Test local development server
python test_website_simple.py

# Test remote website
python test_website_simple.py --url https://your-website.azurewebsites.net

# Save detailed results to a file
python test_website_simple.py --url https://your-website.azurewebsites.net --output test_results.json
```

## Test Scripts

### 1. `test_website_simple.py` (Recommended)
A comprehensive but lightweight test script that verifies:
- ✅ Website accessibility and health
- ✅ Data submission to `/bike-data` endpoint
- ✅ Multiple consecutive submissions
- ✅ Data validation (server rejects invalid data)
- ✅ Performance characteristics

**Advantages:**
- No database access required
- Tests the complete end-to-end API workflow
- Easy to run on any system
- Provides clear pass/fail results

### 2. `test_website_data_recording.py` (Advanced)
A more comprehensive test that includes direct database verification (requires database modules).

### 3. `run_website_test.bat` (Windows Helper)
A Windows batch file that automatically:
- Checks for Python installation
- Installs required packages if needed
- Runs the simple test script
- Provides user-friendly output

## What the Tests Verify

### 1. Website Health Check
- Verifies the `/health` endpoint is responding
- Confirms database connectivity
- Measures response time

### 2. Data Submission Test
- Sends realistic bike sensor data to `/bike-data` endpoint
- Verifies the server processes the data correctly
- Checks that a valid roughness value is returned

### 3. Multiple Submissions Test
- Sends 5 consecutive data submissions
- Verifies consistent processing
- Measures success rate and performance

### 4. Data Validation Test
- Sends invalid data to ensure server validation works
- Tests missing fields, invalid coordinates, empty data
- Confirms the server properly rejects bad data

### 5. Performance Test
- Measures response times under light load
- Verifies response times are reasonable (< 5 seconds average)
- Checks success rate remains high

## Understanding Test Results

### ✅ PASS Results
When you see "PASS" results, it means:
- Your website is accessible and responding
- The `/bike-data` endpoint is working correctly
- Data is being processed and stored in the database
- The server is validating input data properly
- Performance is acceptable

### ❌ FAIL Results
Common failure scenarios and solutions:

**Website Health Check Fails:**
- Check if your website is running
- Verify the URL is correct
- Check network connectivity

**Data Submission Fails:**
- Database connection issues
- Server configuration problems
- Check server logs for detailed errors

**Multiple Submissions Fail:**
- Server overload or timeout issues
- Database performance problems
- Memory or resource constraints

**Performance Issues:**
- Slow database responses
- Server resource constraints
- Network latency

## Sample Test Data

The test scripts generate realistic bike sensor data:
- GPS coordinates (Netherlands region)
- Realistic cycling speeds (15-35 km/h)
- Simulated accelerometer data (60 samples)
- Random device IDs and fingerprints

## Requirements

### Python Requirements
- Python 3.8 or higher
- `requests` library (automatically installed if missing)

### Website Requirements
- Website must be running and accessible
- `/health` endpoint must be available
- `/bike-data` endpoint must be functional
- Database must be connected and operational

## Troubleshooting

### Common Issues

**"Cannot connect to website"**
- Ensure the website URL is correct
- Check if the website is running
- Verify network connectivity
- Try accessing the website in a browser first

**"HTTP 500 errors"**
- Check server logs for detailed error messages
- Verify database connectivity
- Check environment variables and configuration

**"Data validation failed"**
- Check the data format requirements
- Verify the API endpoint is expecting the correct format
- Review server-side validation logic

**"Performance issues"**
- Check server resources (CPU, memory)
- Monitor database performance
- Consider scaling up resources

### Getting More Information

1. **Enable detailed output:**
   ```bash
   python test_website_simple.py --url your-url --output detailed_results.json
   ```

2. **Check the detailed results file** for more information about each test

3. **Check your website's health endpoint directly:**
   Visit `https://your-website.com/health` in a browser

4. **Review server logs** for any error messages during testing

## Integration with Development Workflow

### Local Development
```bash
# Start your local server
python main.py

# In another terminal, run tests
python test_website_simple.py
```

### Production Testing
```bash
# Test your deployed website
python test_website_simple.py --url https://your-app.azurewebsites.net
```

### Continuous Integration
You can integrate these tests into your CI/CD pipeline:
```bash
python test_website_simple.py --url $WEBSITE_URL && echo "Tests passed" || exit 1
```

## Exit Codes

The test scripts return standard exit codes:
- `0`: All tests passed successfully
- `1`: Some tests failed
- `2`: Tests interrupted by user
- `3`: Test runner crashed

This makes it easy to integrate with automation scripts and CI/CD pipelines.

## Support

If you encounter issues with the test scripts:
1. Check that your website is running correctly
2. Verify the URL is accessible in a web browser
3. Review any error messages in the test output
4. Check your website's logs for additional information

The test scripts are designed to provide clear, actionable feedback about what's working and what needs attention.
