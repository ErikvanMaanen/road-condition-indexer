# Python 3.12 Azure Deployment Guide

## Overview

This guide provides instructions for deploying the Road Condition Indexer to Azure App Service running Python 3.12.

## Azure App Service Configuration

### 1. Runtime Stack
- **Runtime stack**: Python 3.12
- **Operating System**: Linux
- **Version**: Python 3.12.x (latest available)

### 2. Application Settings

Add these environment variables in Azure Portal > App Service > Configuration > Application settings:

```
PYTHONUNBUFFERED=1
PYTHONIOENCODING=utf-8
PYTHONWARNINGS=ignore::SyntaxWarning,ignore::DeprecationWarning:azure,ignore::PendingDeprecationWarning
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_LOG_LEVEL=info
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
WEBSITES_MOUNT_ENABLED=1
WEBSITES_CONTAINER_START_TIME_LIMIT=1800
PYTHON_VERSION=3.12
DEBUG=false
```

### 3. Database Connection Settings

Add your Azure SQL Database connection settings:

```
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433
```

### 4. Startup Command Options

**Option 1: Simple (Recommended for Python 3.12)**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
```

**Option 2: Using azure_startup.sh**
```bash
bash azure_startup.sh
```

**Option 3: Using full startup.sh (with ODBC checks)**
```bash
bash startup.sh
```

## Python 3.12 Specific Considerations

### 1. Package Compatibility
- All packages in `requirements.txt` are compatible with Python 3.12
- FastAPI >= 0.104.0 has full Python 3.12 support
- Azure SDK packages >= 1.15.0 are Python 3.12 compatible

### 2. Warning Suppression
Python 3.12 may show fewer warnings than Python 3.13, but we still suppress:
- SyntaxWarnings from Azure SDK
- DeprecationWarnings
- PendingDeprecationWarnings

### 3. Performance Optimizations
- Uvicorn with standard extras for better performance
- Single worker configuration (optimal for Azure App Service)
- Extended timeout settings for Azure environment

## Deployment Steps

### 1. Prepare Your Code
- Ensure all files are committed to your repository
- Update `requirements.txt` with Python 3.12 compatible versions

### 2. Configure Azure App Service
- Set runtime stack to Python 3.12
- Add all application settings listed above
- Configure database connection strings

### 3. Deploy
- Use Azure DevOps, GitHub Actions, or direct deployment
- Monitor deployment logs for any issues

### 4. Verify Deployment
- Check health endpoint: `https://your-app.azurewebsites.net/health`
- Monitor application logs for any warnings or errors
- Test main functionality through the web interface

## Troubleshooting Python 3.12 Issues

### Common Issues

1. **Import Errors**
   - Ensure all packages in requirements.txt are Python 3.12 compatible
   - Check that pyodbc can find ODBC drivers

2. **Performance Issues**
   - Python 3.12 generally performs better than 3.11
   - Monitor memory usage and adjust accordingly

3. **Startup Failures**
   - Check application logs for specific error messages
   - Verify environment variables are set correctly
   - Ensure database connectivity

### Debugging Commands

Run these in the Azure Console (Development Tools > Console):

```bash
# Check Python version
python3 --version

# Test imports
python3 -c "import fastapi; import uvicorn; print('FastAPI imports OK')"

# Check ODBC drivers
odbcinst -q -d -n "ODBC Driver 18 for SQL Server"

# Test database connection (if configured)
python3 -c "import pyodbc; print('ODBC available')"
```

## Performance Expectations

Python 3.12 improvements you should see:
- Faster startup times compared to earlier Python versions
- Better memory efficiency
- Improved error handling and debugging information

## Monitoring

Set up monitoring for:
- Application response times
- Memory usage
- Database connection health
- Error rates and types

Use Azure Application Insights for comprehensive monitoring.
