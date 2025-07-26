# Azure Deployment Fix Guide

## Python Version Support

This application supports **Python 3.12** (recommended) with modern SQLAlchemy-based database architecture:
- **Database Backend**: SQLAlchemy with pymssql driver (no ODBC required)
- **Automatic Fallback**: SQLite for development environments
- **Improved Reliability**: Connection pooling and automatic reconnection

## Major Database Architecture Updates

### **Migrated from pyodbc to SQLAlchemy + pymssql**

**Previous Architecture**: 
- Direct pyodbc connections to SQL Server
- Required Microsoft ODBC Driver installation
- Manual connection management

**New Architecture**:
- SQLAlchemy ORM with pymssql driver
- No ODBC driver dependencies  
- Automatic connection pooling
- Seamless SQLite fallback for development

**Benefits**:
- ✅ Simpler deployment (no ODBC driver required)
- ✅ Better error handling and connection recovery  
- ✅ Zero-configuration development with SQLite
- ✅ Improved performance with connection pooling
- ✅ Cross-platform compatibility

### **Automatic Database Backend Selection**

The application now automatically chooses the appropriate database backend:

```python
# Azure SQL Server (Production)
if all Azure SQL environment variables are provided:
    → Use SQLAlchemy + pymssql
    → Connection pooling enabled
    → Automatic reconnection

# SQLite (Development/Testing)  
if Azure SQL environment variables missing:
    → Use SQLAlchemy + SQLite
    → Local file: RCI_local.db
    → Zero configuration required
```

## Issues Fixed

### 1. SyntaxWarning from Azure SDK (Python 3.12 Compatibility)

**Problem**: Azure Management SDK modules contain invalid escape sequences that trigger SyntaxWarnings in Python 3.12+.

**Solution**: Added comprehensive warning suppression at the top of `main.py`:

```python
import warnings
# Python 3.12 compatible warning suppression for Azure SDK
warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", message="invalid escape sequence", category=SyntaxWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="azure")
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
```

### 2. Enhanced Health Check with Database Testing

**Problem**: Azure App Service was terminating the app due to inadequate health checks.

**Solution**: Improved `/health` endpoint with SQLAlchemy database testing:

```python
@app.get("/health")
def health_check():
    """Health check endpoint for Azure App Service probes."""
    try:
        # Quick database connectivity test using SQLAlchemy
        result = db_manager.execute_scalar("SELECT 1")
        if result == 1:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected"
            }
        else:
            raise Exception("Database test query returned unexpected result")
    except Exception as e:
        # Return 503 Service Unavailable if health check fails
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy", 
                "timestamp": datetime.utcnow().isoformat(),
                "database": "disconnected",
                "error": str(e)
            }
        )
```
```

### 3. Enhanced Database Connectivity and Startup Resilience

**Problem**: Database connection failures and startup issues could crash the application.

**Solution**: Implemented robust database management with SQLAlchemy:
- **Connection Pooling**: Automatic connection management and recovery
- **Fault-Tolerant Startup**: Non-critical errors don't prevent app startup
- **Graceful Degradation**: SQLite fallback when Azure SQL is unavailable
- **Comprehensive Logging**: Detailed startup and connection diagnostics

```python
# Enhanced startup with database backend selection
def startup_init():
    """Initialize with automatic database backend selection."""
    if USE_SQLSERVER:
        log_info("🔧 Using Azure SQL Server backend with pymssql driver")
    else:
        log_info("🔧 Using SQLite backend for development")
    
    db_manager.init_tables()  # Works with both backends
    # Non-critical failures don't crash the application
```

## Azure App Service Configuration

### Application Settings (Environment Variables)

**Required for Production (Python 3.12):**
```
# Python Runtime Configuration
PYTHONUNBUFFERED=1
PYTHONIOENCODING=utf-8
PYTHONWARNINGS=ignore::SyntaxWarning,ignore::DeprecationWarning:azure,ignore::PendingDeprecationWarning
PYTHON_VERSION=3.12

# Uvicorn Server Configuration  
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_LOG_LEVEL=info

# Azure App Service Configuration
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
WEBSITES_MOUNT_ENABLED=1
WEBSITES_CONTAINER_START_TIME_LIMIT=1800

# Database Configuration (Azure SQL Server)
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433

# Application Settings
DEBUG=false
DEBUG=false
```

### Startup Command Options

**Recommended Startup Command (Python 3.12 with SQLAlchemy)**
Use this in your Azure App Service Configuration > General settings > Startup Command:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
```

**Alternative: Database-aware startup script**
Use the provided `azure_startup.sh` script for additional database configuration checks:

```bash
bash azure_startup.sh
```

### Health Check Configuration

Configure Azure App Service health checks:
- **Health check path**: `/health`
- **Interval**: 60 seconds
- **Timeout**: 30 seconds
- **Unhealthy threshold**: 3

The health check endpoint now includes SQLAlchemy database connectivity testing for both Azure SQL and SQLite backends.

## Database Migration Benefits

### **No More ODBC Dependencies**

**Previous Deployment Issues**:
- Required Microsoft ODBC Driver 17/18 installation
- Complex driver configuration and version management
- Platform-specific installation procedures

**Current Deployment (SQLAlchemy + pymssql)**:
- ✅ Zero ODBC dependencies
- ✅ Direct TCP connection to SQL Server
- ✅ Cross-platform compatibility
- ✅ Simplified container deployments

### **Development Environment Improvements**

**Previous Challenges**:
- Required full Azure SQL setup for local development
- Manual database configuration switches

**Current Benefits**:
- ✅ Automatic SQLite fallback for development
- ✅ Zero-configuration local development
- ✅ Identical code paths for both backends

## Updated Requirements

The `requirements.txt` now focuses on SQLAlchemy-based dependencies:

```
# Core database handling
sqlalchemy>=2.0.0
pymssql>=2.2.0            # SQL Server driver (no ODBC required)

# Azure SDK (for management features only)
azure-identity>=1.15.0
azure-mgmt-web>=7.1.0
azure-mgmt-sql>=3.0.0,<4.0.0
```

**Removed Dependencies**:
- `pyodbc` - No longer needed
- ODBC driver system requirements

## Troubleshooting Common Issues

### Database Connection Issues
**Symptoms**: Application fails to start or health checks fail
**Diagnosis**: Check which database backend is being used
**Solutions**:
1. **Azure SQL Issues**: Verify all `AZURE_SQL_*` environment variables
2. **SQLite Fallback**: Check if `RCI_local.db` can be created in app directory
3. **Connection Testing**: Use `python setup_env.py` to verify connectivity

### SyntaxWarnings from Azure SDK
**Symptoms**: Logs show warnings like `invalid escape sequence '\ '` in azure.mgmt.sql.models
**Solution**: Ensure `PYTHONWARNINGS=ignore::SyntaxWarning,ignore::DeprecationWarning:azure` is set in app settings

### App Starts Then Immediately Shuts Down
**Symptoms**: Uvicorn starts successfully but terminates within seconds
**Possible Causes**:
1. Database initialization failures
2. Missing environment variables
3. File system permission issues (SQLite)
**Solutions**:
1. Use recommended startup command: `uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info`
2. Verify database configuration with environment verification script
3. Check Application Insights logs for detailed error information

### SQLite Permissions (Development)
**Symptoms**: SQLite database creation fails locally
**Solution**: Ensure the application directory has write permissions for `RCI_local.db`

## Verification Steps

After deployment, verify the updated database handling:

1. **Check health endpoint**: `curl https://your-app.azurewebsites.net/health`
   - Should return database connection status
   - Indicates which backend is being used

2. **Verify database backend**: Check application logs for:
   - `"Using Azure SQL Server backend"` (production)
   - `"Using SQLite backend"` (development/fallback)

3. **Test data submission**: Submit test data to verify database operations
4. **Monitor performance**: SQLAlchemy connection pooling should improve performance
5. **Check startup time**: Should be faster without ODBC driver checks
4. **Test database connectivity**: Verify data endpoints return properly

## Common Issues

1. **Still seeing SyntaxWarnings**: Ensure the warning filters are at the very top of `main.py`
2. **Health check fails**: Verify database connectivity and credentials
3. **App still crashes**: Check Application Insights for detailed error messages

## Support

If issues persist:
1. Check Azure App Service logs in the Portal
2. Verify all environment variables are set correctly
3. Ensure ODBC Driver 18 for SQL Server is available (should be pre-installed in Azure App Service)
