# SQL Connectivity Testing Documentation

## Overview

The Road Condition Indexer now includes comprehensive SQL connectivity testing that automatically runs during application startup. This ensures reliable database connectivity and provides detailed diagnostics for troubleshooting connection issues.

## Features

### 🚀 Automatic Startup Testing
- **Environment Detection**: Automatically detects Azure App Service vs local development environment
- **Variable Loading**: Loads environment variables from Azure App Settings or local `.env` file
- **Progressive Testing**: Runs tests in logical order (DNS → Port → Auth → Queries → Performance)
- **Fail-Fast**: Critical failures prevent application startup with clear error messages

### 🔍 Comprehensive Test Suite
1. **Environment Validation**: Verifies all required environment variables are present
2. **DNS Resolution**: Tests hostname resolution for the SQL Server
3. **Port Connectivity**: Verifies TCP connectivity to SQL Server port (1433)
4. **Authentication**: Tests SQL Server login with retry logic and exponential backoff
5. **Query Execution**: Validates database access and basic query functionality
6. **Performance Benchmark**: Measures connection and query performance

### 📊 Detailed Reporting
- **Test Results**: Individual test status, duration, and error messages
- **Recommendations**: Specific guidance for fixing detected issues
- **Environment Info**: Summary of configuration and runtime environment
- **Performance Metrics**: Connection times and query performance data

## Configuration

### Azure App Service (Production)
Set the following **Application Settings** in your Azure App Service:

```
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433
```

### Local Development
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your SQL Server details in the `.env` file:
   ```bash
   AZURE_SQL_SERVER=your-server.database.windows.net
   AZURE_SQL_DATABASE=your-database-name
   AZURE_SQL_USER=your-username
   AZURE_SQL_PASSWORD=your-password
   AZURE_SQL_PORT=1433
   ```

3. Install python-dotenv (already included in requirements.txt):
   ```bash
   pip install python-dotenv
   ```

## Usage

### Automatic Testing (Startup)
The SQL connectivity tests run automatically when the application starts:

```bash
# Local development
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Example startup output:**
```
🚀 Application startup initiated
🔍 Running comprehensive SQL connectivity tests...
🏠 Detected local development environment
📁 Loading environment from: /path/to/.env
🔧 Loaded 5 environment variables
✅ Environment Validation: All required environment variables are present (2.1ms)
✅ DNS Resolution: Successfully resolved server.database.windows.net to 1.2.3.4 (45.2ms)
✅ Port Connectivity: Successfully connected to server.database.windows.net:1433 (123.4ms)
✅ Authentication: Successfully authenticated to database 'mydb' (856.7ms)
✅ Query Execution: Successfully executed queries. Database has 12 tables. (45.1ms)
✅ Performance Benchmark: Good performance - Conn: 856.7ms, Avg Query: 23.4ms (234.5ms)
✅ SQL connectivity tests passed - database is ready
```

### Standalone Testing
Run the standalone connectivity test script:

```bash
python tests/test_sql_connectivity.py
```

This provides detailed diagnostics without starting the full application.

## Test Results and Troubleshooting

### Test Status Types
- **✅ SUCCESS**: Test passed successfully
- **⚠️ WARNING**: Test passed but with performance or configuration concerns
- **❌ FAILED**: Test failed and needs attention
- **⏱️ TIMEOUT**: Test timed out (connection or query timeout)
- **🌐 DNS_ERROR**: DNS resolution failed
- **🔑 AUTH_ERROR**: Authentication failed
- **🔌 CONNECTION_ERROR**: Network connection failed

### Common Issues and Solutions

#### Environment Validation Failures
**Problem**: Missing environment variables
```
❌ Environment Validation: Missing required environment variables: AZURE_SQL_PASSWORD
```
**Solution**: Set the missing environment variables in Azure App Service settings or local `.env` file

#### DNS Resolution Failures
**Problem**: Cannot resolve SQL Server hostname
```
❌ DNS Resolution: DNS resolution failed: [Errno 11001] getaddrinfo failed
```
**Solutions**:
- Verify the server name is correct (should end with `.database.windows.net`)
- Check network connectivity
- Verify DNS settings

#### Port Connectivity Failures
**Problem**: Cannot connect to SQL Server port
```
❌ Port Connectivity: Connection refused to server.database.windows.net:1433
```
**Solutions**:
- Check firewall rules (both local and Azure)
- Verify the SQL Server is running and accepting connections
- Ensure port 1433 is not blocked by corporate firewall

#### Authentication Failures
**Problem**: Login credentials rejected
```
🔑 Authentication: Authentication failed: Login failed for user 'username'
```
**Solutions**:
- Verify username and password are correct
- Check if user account exists in the database
- Ensure user has proper permissions
- For Azure SQL, verify firewall allows your IP address

#### Performance Warnings
**Problem**: Slow connection or query performance
```
⚠️ Performance Benchmark: Slow performance detected - Conn: 15234.5ms, Avg Query: 2345.6ms
```
**Solutions**:
- Consider upgrading SQL Server tier
- Check network latency to Azure region
- Optimize database indexes
- Monitor for database resource constraints

## Environment Variable Reference

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_SQL_SERVER` | SQL Server hostname | `myserver.database.windows.net` |
| `AZURE_SQL_DATABASE` | Database name | `RoadConditionDB` |
| `AZURE_SQL_USER` | SQL Server username | `sqladmin` |
| `AZURE_SQL_PASSWORD` | SQL Server password | `MySecurePassword123!` |
| `AZURE_SQL_PORT` | SQL Server port | `1433` |

### Optional Variables  
| Variable | Description | Default |
|----------|-------------|---------|
| `WEBSITE_SITE_NAME` | Azure App Service site name (auto-detected) | None |

## Integration with Application Startup

The SQL connectivity tests are integrated into the application startup sequence:

1. **Environment Detection**: Determines if running in Azure App Service or locally
2. **Variable Loading**: Loads configuration from appropriate source
3. **Connectivity Testing**: Runs comprehensive test suite
4. **Database Initialization**: Proceeds with normal database table setup
5. **Application Ready**: Starts accepting HTTP requests

### Startup Sequence
```
🚀 Application startup initiated
🔍 Running comprehensive SQL connectivity tests...
   [Detailed test results...]
✅ SQL connectivity tests passed - database is ready
🔧 Initializing database tables...
✅ Database tables initialized successfully
🔍 Verifying basic database connectivity...
✅ All required tables verified: 4 tables
📊 Database contains 1234 bike data records
✅ Database integrity check passed
✅ Application startup completed successfully
```

## Performance Monitoring

The connectivity tests include performance benchmarking:

- **Connection Time**: Time to establish database connection
- **Query Performance**: Average execution time for test queries
- **Performance Rating**: Automatic assessment (Excellent/Good/Acceptable/Slow)

### Performance Thresholds
- **Excellent**: Connection < 1s, Queries < 100ms
- **Good**: Connection < 3s, Queries < 500ms  
- **Acceptable**: Connection < 10s, Queries < 1s
- **Slow**: Above acceptable thresholds

## Security Considerations

- **Credential Protection**: Passwords are masked in logs and output
- **Environment Variables**: Sensitive data loaded from secure sources
- **Connection Security**: All connections use encrypted connections to Azure SQL
- **No Hardcoded Secrets**: All configuration externalized to environment variables

## Development Workflow

### Local Development Setup
1. Copy `.env.example` to `.env`
2. Fill in your SQL Server connection details
3. Run `python tests/test_sql_connectivity.py` to verify connectivity
4. Start the application with `python main.py` or `uvicorn main:app`

### Azure Deployment
1. Set Application Settings in Azure App Service
2. Deploy your application
3. Monitor startup logs for connectivity test results
4. Application will fail to start if SQL connectivity is not working

## Troubleshooting Commands

### Test connectivity manually
```bash
python tests/test_sql_connectivity.py
```

### Check environment variables (local)
```bash
# On Windows
echo $env:AZURE_SQL_SERVER

# On Linux/Mac
echo $AZURE_SQL_SERVER
```

### Verify .env file loading
```bash
python -c "from dotenv import load_dotenv; load_dotenv('.env'); import os; print('Server:', os.getenv('AZURE_SQL_SERVER'))"
```

### Test basic SQL Server connectivity
```bash
# Using sqlcmd (if available)
sqlcmd -S your-server.database.windows.net -d your-database -U your-user -P your-password -Q "SELECT 1"
```

## Monitoring and Alerting

The connectivity tests provide structured logging that can be monitored:

- **Startup Success/Failure**: Monitor for application startup failures
- **Performance Degradation**: Alert on slow connection/query times
- **Authentication Issues**: Monitor for credential failures
- **Network Problems**: Alert on DNS or connectivity failures

Log entries include structured data for easy parsing and alerting in Azure Application Insights or other monitoring solutions.
