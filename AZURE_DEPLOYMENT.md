# Azure Web App Deployment Guide

## Azure App Service Configuration

### 1. Startup Command
In Azure Portal → Your App Service → Configuration → General Settings → Startup Command:

**Option A: Direct Command (Recommended)**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 --preload --access-logfile=- --error-logfile=- --log-level info main:app
```

**Option B: Using Startup Script**
```bash
bash azure_startup.sh
```

### 2. Required Application Settings
In Azure Portal → Your App Service → Configuration → Application Settings:

```
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433
```

### 3. Optional Performance Settings
```
PYTHONUNBUFFERED=1
PYTHONIOENCODING=utf-8
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
WEBSITES_CONTAINER_START_TIME_LIMIT=1800
```

### 4. Python Runtime Settings
- **Runtime Stack**: Python 3.12
- **Major Version**: 3.12
- **Minor Version**: Latest

## Startup Process

When your app starts, it will:

1. **Environment Detection** - Automatically detects Azure App Service
2. **Variable Validation** - Checks all required SQL Server variables
3. **SQL Connectivity Tests** - Runs comprehensive connectivity tests:
   - Environment validation
   - DNS resolution
   - Port connectivity  
   - Authentication
   - Query execution
   - Performance benchmarking
4. **Database Initialization** - Sets up required tables
5. **Application Start** - Begins serving HTTP requests

## Expected Startup Logs

```
🚀 Azure App Service startup for Road Condition Indexer (Python 3.12)
📊 Using SQLAlchemy with Azure SQL Server (SQL Server only - no fallback)
✅ Application files found
🐍 Python version: Python 3.12.x
✅ Azure SQL Server configuration detected
   Server: your-server.database.windows.net
   Database: your-database-name
   User: your-username
🔍 SQL connectivity tests will run automatically on startup
✅ No ODBC driver required - using native pymssql connection
🧪 Comprehensive SQL connectivity tests integrated into startup process
🌟 Starting gunicorn with uvicorn workers for production...
🚀 Application startup initiated
🔍 Running comprehensive SQL connectivity tests...
🌐 Detected Azure App Service environment
✅ Environment Validation: All required environment variables are present
✅ DNS Resolution: Successfully resolved server.database.windows.net
✅ Port Connectivity: Successfully connected to server:1433
✅ Authentication: Successfully authenticated to database
✅ Query Execution: Successfully executed queries
✅ Performance Benchmark: Good performance
✅ SQL connectivity tests passed - database is ready
🔧 Initializing database tables...
✅ Database tables initialized successfully
✅ All required tables verified: 4 tables
📊 Database contains X bike data records
✅ Database integrity check passed
✅ Application startup completed successfully
```

## Health Check Configuration

1. Go to Azure Portal → Your App Service → Health check
2. Enable health check
3. Set health check path: `/` (your app's root endpoint)
4. Grace period: 10 minutes (allows time for SQL connectivity tests)

## Monitoring and Troubleshooting

### Application Insights
Enable Application Insights for detailed telemetry:
- Performance metrics
- Exception tracking
- Custom events from SQL connectivity tests
- Request/response logging

### Log Stream
Monitor real-time logs during deployment:
Azure Portal → Your App Service → Log stream

### Common Issues

**Startup Timeout**: If SQL connectivity tests take too long:
- Increase `WEBSITES_CONTAINER_START_TIME_LIMIT` to 1800 (30 minutes)
- Check SQL Server firewall rules
- Verify network connectivity

**Authentication Failures**: If SQL login fails:
- Verify Application Settings values
- Check SQL Server firewall allows Azure services
- Ensure user has proper database permissions

**Performance Issues**: If app starts slowly:
- Monitor SQL connectivity test performance
- Consider upgrading SQL Server tier
- Check network latency to SQL Server region

## Scaling Configuration

For high-traffic applications, adjust worker count:

**Small App Service Plan (S1)**:
```bash
gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 --preload main:app
```

**Standard App Service Plan (S2/S3)**:
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 --preload main:app
```

**Premium App Service Plan (P1V3+)**:
```bash
gunicorn -w 6 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 180 --max-requests 1000 --preload main:app
```

## Deployment Commands

Deploy using Azure CLI:
```bash
# Set up deployment
az webapp deployment source config-zip --resource-group <resource-group> --name <app-name> --src <zip-file>

# Or using GitHub Actions (recommended)
# Configure in Azure Portal → Deployment → Deployment Center
```

The updated startup script and configuration will ensure your Road Condition Indexer starts reliably with comprehensive SQL connectivity validation!
